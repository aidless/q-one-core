"""User-declared life ontology. Measurement semantics precede any arithmetic."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math


class ModelError(ValueError):
    pass


COLLECTIONS = {'dimensions': 64, 'values': 64, 'measures': 256, 'observations': 4096,
               'resources': 64, 'goals': 256, 'hypotheses': 512, 'actions': 128, 'guardrails': 64}


def instant(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ModelError('时间必须包含时区') from exc


def fingerprint(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ModelError('数值必须有限，不能用布尔值替代')
    return value


def interval(value):
    if isinstance(value, dict) and set(value) == {'lower', 'upper'}:
        lo, hi = number(value['lower']), number(value['upper'])
    else:
        lo = hi = number(value)
    if lo > hi:
        raise ModelError('区间下界不能超过上界')
    return {'lower': lo, 'upper': hi}


def text(row, key, limit=2000):
    v = row.get(key)
    if not isinstance(v, str) or not v.strip() or len(v) > limit:
        raise ModelError(f'{key} 应为非空文本，最多{limit}字符')
    return v


def identifiers(value):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value) or len(set(value)) != len(value):
        raise ModelError('关联ID必须为不重复的文本列表')
    return value


def acyclic(rows, field):
    # Iterative traversal also handles long observation correction chains.
    done = set()
    for root in rows:
        if root in done:
            continue
        active, stack = set(), [(root, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                active.remove(key); done.add(key)
                continue
            if key in active:
                raise ModelError(f'{field} 存在循环关联')
            if key in done:
                continue
            active.add(key); stack.append((key, True))
            refs = rows[key].get(field)
            if field != 'depends_on':
                if refs is not None and not isinstance(refs, str):
                    raise ModelError(f'{field} 应为单一ID')
                refs = [refs] if refs else []
            else:
                refs = identifiers(refs or [])
            for ref in reversed(refs):
                if ref not in rows:
                    raise ModelError(f'{field} 引用了不存在的ID')
                stack.append((ref, False))


def measured_value(value, measure):
    if measure['scale'] in {'ratio', 'interval'}:
        result = interval(value)
        if measure['scale'] == 'ratio' and result['lower'] < 0:
            raise ModelError('比率量表的观察值不能为负')
        if 'bounds' in measure:
            bounds = interval(measure['bounds'])
            if result['lower'] < bounds['lower'] or result['upper'] > bounds['upper']:
                raise ModelError('观察值超出该量表声明的有效范围')
        return result
    if measure['scale'] == 'unclassified' and type(value) in (int, float):
        return number(value)
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ModelError('非数量量表应保留文字或类别')
    if measure['scale'] in {'ordinal', 'nominal'} and value not in measure['categories']:
        raise ModelError('观察类别不在预定义类别内')
    return value


def canonical_measured_value(value, measure):
    """Normalize numeric representation for equality, not for arithmetic."""
    result = measured_value(value, measure)
    if isinstance(result, dict):
        return {key: _canonical_number(result[key]) for key in ('lower', 'upper')}
    if type(result) in (int, float):
        return _canonical_number(result)
    return result


def _canonical_number(value):
    normalized = Decimal(str(value)).normalize()
    if normalized == 0:
        return '0'
    return format(normalized, 'f')


def measured_fingerprint(value, measure):
    return fingerprint(canonical_measured_value(value, measure))


def condition(row, measures):
    if not isinstance(row, dict) or row.get('measure_id') not in measures:
        raise ModelError('目标条件必须关联已有测量定义')
    m = measures[row['measure_id']]
    op = row.get('op')
    if op not in {'gte', 'lte', 'between', 'eq'}:
        raise ModelError('条件操作应为gte/lte/between/eq')
    if m['scale'] in {'ratio', 'interval'}:
        if op == 'between':
            interval(row.get('target'))
        else:
            number(row.get('target'))
    elif m['scale'] == 'ordinal':
        if op not in {'gte', 'lte', 'eq'} or row.get('target') not in m['categories']:
            raise ModelError('有序类别只能按声明顺序比较，不能做加减')
    elif op != 'eq' or not isinstance(row.get('target'), str):
        raise ModelError('类别/定性量表只能作文字相等检查')
    elif m['scale'] == 'nominal' and row['target'] not in m['categories']:
        raise ModelError('目标类别无效')


def _validate_model(raw):
    if not isinstance(raw, dict) or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
        raise ModelError('人生模型需要schema_version=1')
    data = deepcopy(raw)
    text(data, 'title', 200)
    indexed = {}
    for name, limit in COLLECTIONS.items():
        rows = data.setdefault(name, [])
        if not isinstance(rows, list) or len(rows) > limit:
            raise ModelError(f'{name} 超过数量限制或格式无效')
        index = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ModelError(f'{name} 记录必须为对象')
            key = text(row, 'id', 120)
            if key in index:
                raise ModelError(f'{name} 含重复ID')
            index[key] = row
        indexed[name] = index
    dims, measures, resources, goals, hypotheses = (indexed[n] for n in ('dimensions','measures','resources','goals','hypotheses'))
    for row in dims.values():
        text(row, 'name', 150)
    acyclic(dims, 'parent_id')
    for row in indexed['values'].values():
        text(row, 'statement')
        # Values are explicit user statements, never inferred from usage.
        if row.get('declared_by') != 'user':
            raise ModelError('价值取舍必须由用户明确声明')
    for m in measures.values():
        text(m, 'name', 150); text(m, 'definition'); text(m, 'unit', 80)
        if m.get('dimension_id') not in dims or m.get('scale') not in {'ratio','interval','ordinal','nominal','qualitative','unclassified'}:
            raise ModelError('测量定义缺少有效维度或量表类型')
        if type(m.get('freshness_days')) is not int or not 1 <= m['freshness_days'] <= 3660:
            raise ModelError('每个测量需声明1到3660天的有效期')
        if m.get('persistence', 'unknown') not in {'hold', 'unknown'}:
            raise ModelError('情景中的状态延续只能为hold或unknown')
        if m['scale'] in {'ordinal','nominal'}:
            if not 2 <= len(identifiers(m.get('categories'))) <= 30:
                raise ModelError('类别量表需要2到30个明确类别')
        if 'bounds' in m:
            if m['scale'] not in {'ratio','interval'}:
                raise ModelError('非数量量表不能声明数值范围')
            interval(m['bounds'])
    obs = indexed['observations']
    replaced = set()
    for row in obs.values():
        if row.get('measure_id') not in measures or row.get('source_kind') not in {'user_report','device_record','document_record'}:
            raise ModelError('观察必须关联测量并注明人工、设备或文档来源；模型假设不能写成观察')
        text(row, 'source')
        if instant(row['recorded_at']) < instant(row['observed_at']):
            raise ModelError('不能在观察发生前登记观察事实')
        measured_value(row.get('value'), measures[row['measure_id']])
        old = row.get('supersedes')
        if old:
            if old not in obs or old in replaced or obs[old]['measure_id'] != row['measure_id'] or instant(obs[old]['recorded_at']) > instant(row['recorded_at']):
                raise ModelError('观察更正应为同一测量的单一版本链')
            replaced.add(old)
    acyclic(obs, 'supersedes')
    for r in resources.values():
        text(r, 'name', 150); text(r, 'unit', 80)
        if r.get('budget') is not None and number(r['budget']) < 0:
            raise ModelError('资源预算不能为负')
        if instant(r['valid_from']) >= instant(r['valid_until']):
            raise ModelError('资源预算需要非空的有效时间窗')
    for g in goals.values():
        text(g, 'title', 200); text(g, 'success_criterion')
        if g.get('dimension_id') not in dims or not isinstance(g.get('conditions', []), list):
            raise ModelError('目标应关联维度和明确条件')
        for value_id in identifiers(g.get('value_ids', [])):
            if value_id not in indexed['values']:
                raise ModelError('目标引用了不存在的价值声明')
        for c in g.get('conditions', []):
            condition(c, measures)
        if g.get('deadline'):
            instant(g['deadline'])
        if type(g.get('active', True)) is not bool:
            raise ModelError('目标active应为布尔值')
    acyclic(goals, 'parent_id')
    for h in hypotheses.values():
        text(h, 'statement'); text(h, 'source')
        if h.get('status') not in {'unverified','supported','refuted'} or h.get('origin') not in {'user','model','external'}:
            raise ModelError('影响假设需区分来源与支持状态')
    for a in indexed['actions'].values():
        for key in ('title','first_step','done_when'):
            text(a, key)
        if type(a.get('minutes')) is not int or not 5 <= a['minutes'] <= 480:
            raise ModelError('单次行动需要5到480分钟的完整投入估计')
        for g in identifiers(a.get('goal_ids', [])):
            if g not in goals:
                raise ModelError('行动引用了不存在的目标')
        identifiers(a.get('depends_on', []))
        for name in ('costs','effects'):
            if not isinstance(a.get(name, []), list):
                raise ModelError('行动消耗与影响必须为列表')
        for cost in a.get('costs', []):
            if not isinstance(cost, dict) or cost.get('resource_id') not in resources:
                raise ModelError('行动消耗需要关联资源账户')
            if cost.get('unit') != resources[cost['resource_id']]['unit'] or interval(cost['amount'])['lower'] < 0:
                raise ModelError('资源单位不一致或消耗为负；不会隐式换算')
        for effect in a.get('effects', []):
            if not isinstance(effect, dict) or effect.get('measure_id') not in measures or effect.get('hypothesis_id') not in hypotheses:
                raise ModelError('每个影响需关联测量及影响假设')
            m = measures[effect['measure_id']]
            if type(effect.get('lag_days', 0)) is not int or not 0 <= effect.get('lag_days', 0) <= 3660:
                raise ModelError('影响延迟需要0到3660天的整数')
            if effect.get('mode') == 'delta':
                if m['scale'] not in {'ratio','interval'} or effect.get('unit') != m['unit']:
                    raise ModelError('增量只能用于单位匹配的数量量表')
                interval(effect['amount'])
            elif effect.get('mode') == 'set':
                measured_value(effect.get('value'), m)
            else:
                raise ModelError('影响只能为delta或set')
    acyclic(indexed['actions'], 'depends_on')
    for guard in indexed['guardrails'].values():
        text(guard, 'label'); condition(guard.get('condition'), measures)
    order = identifiers(data.setdefault('goal_order', []))
    if any(g not in goals for g in order):
        raise ModelError('价值取舍顺序引用了不存在的目标')
    return data


def validate_model(raw):
    try:
        return _validate_model(raw)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ModelError('人生模型字段缺失或格式错误') from exc
