"""
EVOLUTION AI 自主学习引擎 - 后端集成模块

核心能力：
1. 6维度A级曲面质量评估（比例协调性、曲面连续性、标杆逼近度、美学评分、国标合规性、创新性）
2. 遗传算法参数优化（种群选择、交叉、变异）
3. 迭代学习循环+收敛检测
4. 智能涌现检测
5. 全时自主学习后台服务

架构：
  评估函数 → 适应度评分 → 遗传算法选择/交叉/变异 → 新一代参数 → 迭代
"""

import math
import json
import random
import copy
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable


class SurfaceQualityEvaluator:
    """A级曲面质量评估器 - 6维度评分体系"""

    GOLDEN_RATIO = 1.618033988749895

    WEIGHTS = {
        'proportion': 0.20,
        'continuity': 0.20,
        'benchmark': 0.25,
        'aesthetic': 0.15,
        'gb_compliance': 0.10,
        'innovation': 0.10,
    }

    def __init__(self, benchmark_data=None):
        self.benchmark = benchmark_data or {}
        self.history = []

    def evaluate(self, params):
        """综合评估，返回0-100分"""
        scores = {
            'proportion': self._score_proportion(params),
            'continuity': self._score_continuity(params),
            'benchmark': self._score_benchmark(params),
            'aesthetic': self._score_aesthetic(params),
            'gb_compliance': self._score_gb_compliance(params),
            'innovation': self._score_innovation(params),
        }

        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)

        result = {
            'total': round(total, 2),
            'scores': {k: round(v, 2) for k, v in scores.items()},
            'params': copy.deepcopy(params),
            'timestamp': datetime.now().isoformat(),
        }
        self.history.append(result)
        return result

    def _score_proportion(self, p):
        """比例协调性评分（0-100）"""
        score = 100

        wb_ratio = p['WB'] / p['L']
        if 0.57 <= wb_ratio <= 0.62:
            pass
        elif 0.55 <= wb_ratio <= 0.65:
            score -= 10 * min(abs(wb_ratio - 0.595) / 0.025, 1)
        else:
            score -= 20

        hw_ratio = p['H'] / p['W']
        if p['H'] > 1.60:
            if 0.85 <= hw_ratio <= 0.92:
                pass
            else:
                score -= 15
        else:
            if 0.70 <= hw_ratio <= 0.78:
                pass
            else:
                score -= 15

        fo_ratio = p['FO'] / p['L']
        if 0.15 <= fo_ratio <= 0.20:
            pass
        else:
            score -= 10

        tw_ratio = p['TW'] / p['W']
        if 0.80 <= tw_ratio <= 0.88:
            pass
        else:
            score -= 10

        waist_ratio = (p['GC'] + p['WL']) / p['H']
        if 0.55 <= waist_ratio <= 0.65:
            pass
        else:
            score -= 10

        return max(0, score)

    def _score_continuity(self, p):
        """曲面连续性评分（0-100）"""
        score = 100

        h = self._derive(p)

        if 20 <= p['AA'] <= 35:
            pass
        else:
            score -= 15

        if 25 <= p['CA'] <= 50:
            pass
        else:
            score -= 15

        if h['hoodY'] < h['waistY']:
            pass
        else:
            score -= 30

        if h['aTopX'] < h['cTopX']:
            pass
        else:
            score -= 30

        if h['wcy'] > p['GC']:
            pass
        else:
            score -= 20

        if h['cabinW'] < h['frontFenderW']:
            pass
        else:
            score -= 10

        return max(0, score)

    def _score_benchmark(self, p):
        """标杆逼近度评分（0-100）"""
        if not self.benchmark:
            return 50

        score = 100
        dims = ['L', 'W', 'H', 'WB', 'GC']

        for dim in dims:
            if dim in self.benchmark and dim in p:
                error = abs(p[dim] - self.benchmark[dim])
                error_mm = error * 1000
                if error_mm <= 5:
                    pass
                elif error_mm <= 20:
                    score -= 5
                elif error_mm <= 50:
                    score -= 10
                elif error_mm <= 100:
                    score -= 20
                else:
                    score -= 30

        return max(0, score)

    def _score_aesthetic(self, p):
        """美学评分（0-100）"""
        score = 100

        lh_ratio = p['L'] / p['H']
        if 3.0 <= lh_ratio <= 3.5:
            pass
        elif 2.8 <= lh_ratio <= 3.8:
            score -= 5
        else:
            score -= 15

        fo_ro_ratio = p['FO'] / p['RO'] if p['RO'] > 0 else 2
        if 0.7 <= fo_ro_ratio <= 1.3:
            pass
        else:
            score -= 10

        wr_h_ratio = p['WR'] / p['H']
        if 0.20 <= wr_h_ratio <= 0.28:
            pass
        else:
            score -= 10

        fwx = p['FO']
        rwx = p['L'] - p['RO']
        front_space = fwx
        rear_space = p['RO']
        balance = min(front_space, rear_space) / max(front_space, rear_space)
        score -= (1 - balance) * 15

        return max(0, score)

    def _score_gb_compliance(self, p):
        """国标合规性评分（0-100）"""
        score = 100

        if p['L'] > 5.3:
            score -= 20
        if p['W'] > 2.55:
            score -= 20
        if p['H'] > 4.0:
            score -= 20
        if p['GC'] < 0.13:
            score -= 15

        if p['WB'] >= p['L']:
            score -= 20

        if p['FO'] + p['RO'] >= p['L']:
            score -= 20

        return max(0, score)

    def _score_innovation(self, p):
        """创新性评分（0-100）"""
        score = 50

        gc_h_ratio = p['GC'] / p['H']
        if 0.08 <= gc_h_ratio <= 0.12:
            score += 10

        wb_ratio = p['WB'] / p['L']
        if wb_ratio >= 0.60:
            score += 10

        tw_ratio = p['TW'] / p['W']
        if tw_ratio >= 0.84:
            score += 10

        if p['WR'] >= 0.35:
            score += 5

        if p['AA'] <= 25:
            score += 5

        return min(100, score)

    def _derive(self, p):
        """硬点推导"""
        fwx = p['FO']
        rwx = p['L'] - p['RO']
        wcy = p['GC'] + p['WR']
        waistY = p['GC'] + p['WL']
        hoodY = p['GC'] + 0.66
        if hoodY >= waistY:
            hoodY = waistY - 0.05
        aBaseX = fwx + 0.10
        aTopY = p['H'] * 0.92
        aTopX = aBaseX + (aTopY - waistY) / math.tan(p['AA'] * math.pi / 180)
        cBaseX = rwx + 0.30
        cTopX = cBaseX - 0.50
        cabinW = p['W'] / 2 * 0.86
        frontFenderW = p['W'] / 2 * 0.95
        return {
            'fwx': fwx,
            'rwx': rwx,
            'wcy': wcy,
            'hoodY': hoodY,
            'waistY': waistY,
            'aTopX': aTopX,
            'cTopX': cTopX,
            'cabinW': cabinW,
            'frontFenderW': frontFenderW,
        }


class GeneticOptimizer:
    """遗传算法参数优化器"""

    PARAM_RANGES = {
        'L': (3.5, 5.5),
        'W': (1.4, 2.2),
        'H': (1.1, 2.0),
        'WB': (2.3, 3.6),
        'FO': (0.6, 1.1),
        'RO': (0.7, 1.4),
        'GC': (0.08, 0.25),
        'WR': (0.25, 0.42),
        'TW': (1.2, 1.8),
        'AA': (18, 35),
        'CA': (25, 55),
        'WL': (0.50, 1.10),
        'WBulge': (0.01, 0.08),
    }

    def __init__(self, evaluator, population_size=20, elite_ratio=0.2,
                 mutation_rate=0.15, crossover_rate=0.7):
        self.evaluator = evaluator
        self.pop_size = population_size
        self.elite_ratio = elite_ratio
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.generation = 0
        self.best_ever = None
        self.best_score_ever = 0
        self.convergence_history = []

    def create_individual(self, base_params=None):
        """创建个体（参数组合）"""
        if base_params:
            ind = copy.deepcopy(base_params)
        else:
            ind = {}
            for key, (lo, hi) in self.PARAM_RANGES.items():
                ind[key] = random.uniform(lo, hi)
        return ind

    def create_population(self, seed_params=None):
        """创建初始种群"""
        population = []
        if seed_params:
            population.append(copy.deepcopy(seed_params))
            for _ in range(self.pop_size - 1):
                ind = self._mutate(copy.deepcopy(seed_params), strength=0.3)
                population.append(ind)
        else:
            for _ in range(self.pop_size):
                population.append(self.create_individual())
        return population

    def evaluate_population(self, population):
        """评估种群"""
        results = []
        for ind in population:
            result = self.evaluator.evaluate(ind)
            results.append((ind, result['total'], result))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def select(self, evaluated):
        """选择（锦标赛选择）"""
        elite_n = max(2, int(self.pop_size * self.elite_ratio))
        elites = [ind for ind, _, _ in evaluated[:elite_n]]
        return elites

    def crossover(self, parent1, parent2):
        """交叉（均匀交叉）"""
        child1 = copy.deepcopy(parent1)
        child2 = copy.deepcopy(parent2)

        for key in self.PARAM_RANGES:
            if random.random() < 0.5:
                child1[key], child2[key] = child2[key], child1[key]

        return child1, child2

    def _mutate(self, individual, strength=None):
        """变异（高斯变异）"""
        s = strength or self.mutation_rate
        for key, (lo, hi) in self.PARAM_RANGES.items():
            if random.random() < s:
                range_size = hi - lo
                delta = random.gauss(0, range_size * 0.1)
                individual[key] = max(lo, min(hi, individual[key] + delta))
        return individual

    def evolve(self, population):
        """一代进化"""
        self.generation += 1

        evaluated = self.evaluate_population(population)

        best_ind, best_score, best_result = evaluated[0]
        if best_score > self.best_score_ever:
            self.best_score_ever = best_score
            self.best_ever = copy.deepcopy(best_ind)

        avg_score = sum(s for _, s, _ in evaluated) / len(evaluated)
        self.convergence_history.append({
            'generation': self.generation,
            'best': best_score,
            'average': round(avg_score, 2),
            'best_ever': self.best_score_ever,
        })

        elites = self.select(evaluated)
        new_population = list(elites)

        while len(new_population) < self.pop_size:
            p1 = random.choice(elites)
            p2 = random.choice(elites)

            if random.random() < self.crossover_rate:
                c1, c2 = self.crossover(p1, p2)
            else:
                c1, c2 = copy.deepcopy(p1), copy.deepcopy(p2)

            c1 = self._mutate(c1)
            c2 = self._mutate(c2)

            new_population.append(c1)
            if len(new_population) < self.pop_size:
                new_population.append(c2)

        return new_population, best_result, evaluated


class EmergenceDetector:
    """智能涌现检测器"""

    def __init__(self):
        self.emergence_events = []

    def detect(self, history):
        """检测涌现事件"""
        if len(history) < 5:
            return []

        events = []

        for i in range(1, len(history)):
            prev_score = history[i - 1].get('best_score', history[i - 1].get('best', 0))
            curr_score = history[i].get('best_score', history[i].get('best', 0))
            delta = curr_score - prev_score
            if delta > 5:
                events.append({
                    'type': 'score_jump',
                    'generation': history[i]['generation'],
                    'delta': round(delta, 2),
                    'description': f"Gen {history[i]['generation']}: 分数跃迁 +{delta:.1f}",
                })

        if 'best_scores' in history[0]:
            dims = history[0]['best_scores'].keys()
            for dim in dims:
                for i in range(1, len(history)):
                    prev = history[i - 1]['best_scores'].get(dim, 0)
                    curr = history[i]['best_scores'].get(dim, 0)
                    if prev < 60 and curr >= 80:
                        events.append({
                            'type': 'dimension_breakthrough',
                            'dimension': dim,
                            'generation': history[i]['generation'],
                            'prev': round(prev, 1),
                            'curr': round(curr, 1),
                            'description': f"Gen {history[i]['generation']}: {dim}维度突破 {prev:.1f}→{curr:.1f}",
                        })

        best_ever = 0
        plateau_count = 0
        for h in history:
            h_best = h.get('best_score', h.get('best', 0))
            if h_best > best_ever:
                if plateau_count >= 5:
                    events.append({
                        'type': 'plateau_breakthrough',
                        'generation': h['generation'],
                        'plateau_length': plateau_count,
                        'description': f"Gen {h['generation']}: 平台突破（停滞{plateau_count}代后提升）",
                    })
                best_ever = h_best
                plateau_count = 0
            else:
                plateau_count += 1

        self.emergence_events = events
        return events


class IterativeLearner:
    """迭代学习引擎"""

    def __init__(self, optimizer, max_generations=100, convergence_window=10,
                 convergence_threshold=0.5, patience=20):
        self.optimizer = optimizer
        self.max_gen = max_generations
        self.conv_window = convergence_window
        self.conv_threshold = convergence_threshold
        self.patience = patience
        self.is_running = False
        self.results = []
        self._callback = None

    def check_convergence(self):
        """收敛检测"""
        history = self.optimizer.convergence_history
        if len(history) < self.conv_window:
            return False

        recent = [h['best'] for h in history[-self.conv_window:]]
        variation = max(recent) - min(recent)
        return variation < self.conv_threshold

    def check_plateau(self):
        """平台检测"""
        history = self.optimizer.convergence_history
        if len(history) < self.patience:
            return False

        recent_best = [h['best_ever'] for h in history[-self.patience:]]
        return len(set(recent_best)) == 1

    def learn(self, seed_params, callback=None):
        """执行迭代学习"""
        self.is_running = True
        self._callback = callback
        population = self.optimizer.create_population(seed_params)

        start_time = time.time()

        for gen in range(self.max_gen):
            if not self.is_running:
                break

            population, best_result, evaluated = self.optimizer.evolve(population)

            gen_info = {
                'generation': gen + 1,
                'best_score': best_result['total'],
                'best_scores': best_result['scores'],
                'best_params': best_result['params'],
                'elapsed': round(time.time() - start_time, 1),
            }
            self.results.append(gen_info)

            if callback:
                callback(gen_info)

            if self.check_convergence():
                gen_info['converged'] = True
                gen_info['convergence_reason'] = 'score_variation < threshold'
                break

            if self.check_plateau():
                self.optimizer.mutation_rate = min(0.4, self.optimizer.mutation_rate * 1.5)
                gen_info['plateau_detected'] = True

        self.is_running = False

        final = {
            'total_generations': len(self.results),
            'best_score': self.optimizer.best_score_ever,
            'best_params': self.optimizer.best_ever,
            'convergence_history': self.optimizer.convergence_history,
            'elapsed': round(time.time() - start_time, 1),
        }
        return final

    def stop(self):
        """停止学习"""
        self.is_running = False

    def reset(self):
        """重置学习器状态"""
        self.is_running = False
        self.results = []
        self.optimizer.generation = 0
        self.optimizer.best_ever = None
        self.optimizer.best_score_ever = 0
        self.optimizer.convergence_history = []


class LearningEngine:
    """自主学习引擎 - 后端服务接口"""

    DEFAULT_PARAMS = {
        'L': 5.10, 'W': 1.99, 'H': 1.51, 'WB': 3.06,
        'FO': 0.85, 'RO': 1.19, 'GC': 0.14, 'WR': 0.33, 'TW': 1.66,
        'AA': 26, 'CA': 40, 'WL': 0.82, 'WBulge': 0.03
    }

    BENCHMARKS = {
        'sedan_c': {'L': 5.101, 'W': 1.987, 'H': 1.509, 'WB': 3.060, 'GC': 0.140},
        'sedan_d': {'L': 5.290, 'W': 1.921, 'H': 1.503, 'WB': 3.216, 'GC': 0.130},
        'suv_full': {'L': 5.060, 'W': 2.004, 'H': 1.779, 'WB': 3.105, 'GC': 0.220},
        'coupe': {'L': 4.519, 'W': 1.852, 'H': 1.298, 'WB': 2.450, 'GC': 0.120},
        'sports': {'L': 4.565, 'W': 1.958, 'H': 1.186, 'WB': 2.600, 'GC': 0.100},
        'mpv': {'L': 5.338, 'W': 1.978, 'H': 1.867, 'WB': 3.198, 'GC': 0.155},
    }

    SEED_MODELS = {
        'sedan_c': {
            'name': 'C级轿车', 'L': 5.10, 'W': 1.99, 'H': 1.51, 'WB': 3.06,
            'FO': 0.85, 'RO': 1.19, 'GC': 0.14, 'WR': 0.33, 'TW': 1.66,
            'AA': 26, 'CA': 40, 'WL': 0.82, 'WBulge': 0.03
        },
        'sedan_d': {
            'name': 'D级轿车', 'L': 5.29, 'W': 1.92, 'H': 1.50, 'WB': 3.22,
            'FO': 0.82, 'RO': 1.25, 'GC': 0.13, 'WR': 0.35, 'TW': 1.62,
            'AA': 26, 'CA': 38, 'WL': 0.77, 'WBulge': 0.02
        },
        'suv_full': {
            'name': '大型SUV', 'L': 5.06, 'W': 2.00, 'H': 1.78, 'WB': 3.11,
            'FO': 0.88, 'RO': 1.07, 'GC': 0.22, 'WR': 0.38, 'TW': 1.68,
            'AA': 28, 'CA': 46, 'WL': 0.85, 'WBulge': 0.02
        },
        'coupe': {
            'name': '轿跑', 'L': 4.52, 'W': 1.85, 'H': 1.30, 'WB': 2.45,
            'FO': 0.93, 'RO': 1.14, 'GC': 0.12, 'WR': 0.34, 'TW': 1.54,
            'AA': 22, 'CA': 35, 'WL': 0.66, 'WBulge': 0.04
        },
        'sports': {
            'name': '超跑', 'L': 4.57, 'W': 1.96, 'H': 1.22, 'WB': 2.60,
            'FO': 0.88, 'RO': 1.09, 'GC': 0.10, 'WR': 0.35, 'TW': 1.68,
            'AA': 24, 'CA': 32, 'WL': 0.63, 'WBulge': 0.05
        },
        'mpv': {
            'name': 'MPV', 'L': 5.34, 'W': 1.98, 'H': 1.88, 'WB': 3.20,
            'FO': 0.84, 'RO': 1.30, 'GC': 0.16, 'WR': 0.35, 'TW': 1.70,
            'AA': 28, 'CA': 58, 'WL': 0.97, 'WBulge': 0.02
        },
    }

    def __init__(self):
        self.evaluator = None
        self.optimizer = None
        self.learner = None
        self.detector = None
        self.is_auto_running = False
        self._auto_timer = None
        self._auto_interval = 10000
        self._current_session = None

    def init_engine(self, benchmark_key: Optional[str] = None):
        """初始化学习引擎"""
        benchmark = self.BENCHMARKS.get(benchmark_key, {}) if benchmark_key else {}
        self.evaluator = SurfaceQualityEvaluator(benchmark)
        self.optimizer = GeneticOptimizer(self.evaluator)
        self.learner = IterativeLearner(self.optimizer)
        self.detector = EmergenceDetector()

    def evaluate_params(self, params: Dict[str, float]) -> Dict[str, Any]:
        """评估参数组合"""
        if not self.evaluator:
            self.init_engine()
        return self.evaluator.evaluate(params)

    def run_learning(self, seed_params: Optional[Dict[str, float]] = None,
                     generations: int = 50, population_size: int = 20,
                     callback: Optional[Callable] = None) -> Dict[str, Any]:
        """运行单次学习会话"""
        if not self.evaluator:
            self.init_engine()

        if seed_params:
            params = {k: v for k, v in seed_params.items() if k != 'name'}
        else:
            params = self.DEFAULT_PARAMS

        initial = self.evaluator.evaluate(params)

        self.optimizer = GeneticOptimizer(
            self.evaluator,
            population_size=population_size,
            elite_ratio=0.2,
            mutation_rate=0.15,
            crossover_rate=0.7,
        )

        self.learner = IterativeLearner(
            self.optimizer,
            max_generations=generations,
            convergence_window=10,
            convergence_threshold=0.5,
            patience=15,
        )

        final = self.learner.learn(params, callback)

        emergence = self.detector.detect(self.learner.results)

        final_eval = self.evaluator.evaluate(final['best_params'])

        return {
            'initial_score': initial['total'],
            'final_score': final_eval['total'],
            'improvement': final_eval['total'] - initial['total'],
            'best_params': final['best_params'],
            'generations': final['total_generations'],
            'elapsed': final['elapsed'],
            'emergence_events': emergence,
            'convergence_history': final['convergence_history'],
            'initial_scores': initial['scores'],
            'final_scores': final_eval['scores'],
        }

    def run_model_learning(self, model_key: str, generations: int = 50,
                           population_size: int = 20) -> Dict[str, Any]:
        """运行预定义车型学习"""
        if model_key not in self.SEED_MODELS:
            raise ValueError(f"Unknown model key: {model_key}. Available: {list(self.SEED_MODELS.keys())}")

        seed_params = self.SEED_MODELS[model_key]
        benchmark = self.BENCHMARKS.get(model_key, {})

        self.init_engine(benchmark_key=model_key)

        return {
            'model_key': model_key,
            'model_name': seed_params.get('name', model_key),
            **self.run_learning(seed_params, generations, population_size),
        }

    def start_auto_learning(self, seed_params: Optional[Dict[str, float]] = None,
                            interval: int = 10000, generations: int = 20,
                            callback: Optional[Callable] = None):
        """启动全时自主学习"""
        if self.is_auto_running:
            self.stop_auto_learning()

        self._auto_interval = interval
        self._current_session = {
            'seed_params': seed_params or self.DEFAULT_PARAMS,
            'generations': generations,
            'callback': callback,
            'history': [],
        }

        self.is_auto_running = True
        self._run_auto_cycle()

    def _run_auto_cycle(self):
        """执行一次自动学习周期"""
        if not self.is_auto_running:
            return

        try:
            result = self.run_learning(
                seed_params=self._current_session['seed_params'],
                generations=self._current_session['generations'],
            )

            self._current_session['seed_params'] = result['best_params']
            self._current_session['history'].append(result)

            if self._current_session['callback']:
                self._current_session['callback'](result)

        except Exception as e:
            pass

        if self.is_auto_running:
            self._auto_timer = time.sleep(self._auto_interval / 1000)
            self._run_auto_cycle()

    def stop_auto_learning(self):
        """停止全时自主学习"""
        self.is_auto_running = False
        if self._auto_timer:
            self._auto_timer = None
        if self.learner:
            self.learner.stop()

    def get_auto_status(self) -> Dict[str, Any]:
        """获取全时学习状态"""
        return {
            'is_running': self.is_auto_running,
            'interval': self._auto_interval,
            'session': self._current_session,
        }

    def get_param_ranges(self) -> Dict[str, Tuple[float, float]]:
        """获取参数范围约束"""
        return GeneticOptimizer.PARAM_RANGES

    def get_weights(self) -> Dict[str, float]:
        """获取各维度权重"""
        return SurfaceQualityEvaluator.WEIGHTS

    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用车型列表"""
        return [
            {
                'key': key,
                'name': model['name'],
                'params': {k: v for k, v in model.items() if k != 'name'},
            }
            for key, model in self.SEED_MODELS.items()
        ]
