#!/usr/bin/env python3
"""
EVOLUTION AI 自主学习引擎 v1.0

核心能力：
1. 6维度A级曲面质量评估
2. 遗传算法参数优化
3. 迭代学习循环+收敛检测
4. 智能涌现：自动发现最优造型参数

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

# ============================================================
# 第一部分：A级曲面质量评估函数（6维度评分体系）
# ============================================================

class SurfaceQualityEvaluator:
    """A级曲面质量评估器"""
    
    # 黄金比例
    GOLDEN_RATIO = 1.618033988749895
    
    # 各维度权重
    WEIGHTS = {
        'proportion': 0.20,    # 比例协调性
        'continuity': 0.20,    # 曲面连续性
        'benchmark': 0.25,     # 标杆逼近度
        'aesthetic': 0.15,     # 美学评分
        'gb_compliance': 0.10, # 国标合规性
        'innovation': 0.10,    # 创新性
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
        
        # 轴距/车长比（理想0.57-0.62）
        wb_ratio = p['WB'] / p['L']
        if 0.57 <= wb_ratio <= 0.62:
            score -= 0
        elif 0.55 <= wb_ratio <= 0.65:
            score -= 10 * min(abs(wb_ratio - 0.595) / 0.025, 1)
        else:
            score -= 20
        
        # 高宽比（轿车0.70-0.78, SUV 0.85-0.92）
        hw_ratio = p['H'] / p['W']
        if p['H'] > 1.60:  # SUV
            if 0.85 <= hw_ratio <= 0.92:
                pass
            else:
                score -= 15
        else:  # 轿车
            if 0.70 <= hw_ratio <= 0.78:
                pass
            else:
                score -= 15
        
        # 前悬/车长比（0.15-0.20）
        fo_ratio = p['FO'] / p['L']
        if 0.15 <= fo_ratio <= 0.20:
            pass
        else:
            score -= 10
        
        # 轮距/车宽比（0.80-0.88）
        tw_ratio = p['TW'] / p['W']
        if 0.80 <= tw_ratio <= 0.88:
            pass
        else:
            score -= 10
        
        # 腰线/车高比（0.55-0.65）
        waist_ratio = (p['GC'] + p['WL']) / p['H']
        if 0.55 <= waist_ratio <= 0.65:
            pass
        else:
            score -= 10
        
        return max(0, score)
    
    def _score_continuity(self, p):
        """曲面连续性评分（0-100）"""
        score = 100
        
        # 检查硬点推导是否产生合理的几何
        h = self._derive(p)
        
        # A柱角合理性（20-35°）
        if 20 <= p['AA'] <= 35:
            pass
        else:
            score -= 15
        
        # C柱角合理性（25-50°）
        if 25 <= p['CA'] <= 50:
            pass
        else:
            score -= 15
        
        # 发动机盖高度必须低于腰线
        if h['hoodY'] < h['waistY']:
            pass
        else:
            score -= 30
        
        # A柱顶必须在C柱顶前方
        if h['aTopX'] < h['cTopX']:
            pass
        else:
            score -= 30
        
        # 轮心高度必须高于离地间隙
        if h['wcy'] > p['GC']:
            pass
        else:
            score -= 20
        
        # 乘员舱宽度必须小于翼子板宽度（tumblehome）
        if h['cabinW'] < h['frontFenderW']:
            pass
        else:
            score -= 10
        
        return max(0, score)
    
    def _score_benchmark(self, p):
        """标杆逼近度评分（0-100）"""
        if not self.benchmark:
            return 50  # 无标杆数据时给中间分
        
        score = 100
        dims = ['L', 'W', 'H', 'WB', 'GC']
        
        for dim in dims:
            if dim in self.benchmark and dim in p:
                error = abs(p[dim] - self.benchmark[dim])
                error_mm = error * 1000
                if error_mm <= 5:
                    pass  # 精确
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
        """美学评分（0-100）- 基于黄金比例和视觉平衡"""
        score = 100
        
        # 车身长高比接近黄金比例（3.0-3.5为最佳）
        lh_ratio = p['L'] / p['H']
        if 3.0 <= lh_ratio <= 3.5:
            pass
        elif 2.8 <= lh_ratio <= 3.8:
            score -= 5
        else:
            score -= 15
        
        # 前后悬比例（接近1:1为最佳）
        fo_ro_ratio = p['FO'] / p['RO'] if p['RO'] > 0 else 2
        if 0.7 <= fo_ro_ratio <= 1.3:
            pass
        else:
            score -= 10
        
        # 轮径与车高比例（0.20-0.28为最佳）
        wr_h_ratio = p['WR'] / p['H']
        if 0.20 <= wr_h_ratio <= 0.28:
            pass
        else:
            score -= 10
        
        # 轴距内前后轮拱对称性
        fwx = p['FO']
        rwx = p['L'] - p['RO']
        front_space = fwx  # 前轴到车头
        rear_space = p['RO']  # 后轴到车尾
        balance = min(front_space, rear_space) / max(front_space, rear_space)
        score -= (1 - balance) * 15
        
        return max(0, score)
    
    def _score_gb_compliance(self, p):
        """国标合规性评分（0-100）"""
        score = 100
        
        # GB 1589-2016 外廓尺寸限值
        if p['L'] > 5.3: score -= 20  # 乘用车车长限值
        if p['W'] > 2.55: score -= 20  # 车宽限值
        if p['H'] > 4.0: score -= 20   # 车高限值
        if p['GC'] < 0.13: score -= 15  # 最小离地间隙
        
        # 轴距必须小于车长
        if p['WB'] >= p['L']: score -= 20
        
        # 前后悬之和必须小于车长
        if p['FO'] + p['RO'] >= p['L']: score -= 20
        
        return max(0, score)
    
    def _score_innovation(self, p):
        """创新性评分（0-100）- 奖励独特但合理的参数组合"""
        score = 50  # 基础分
        
        # 低重心奖励（跑车/SUV低重心设计）
        gc_h_ratio = p['GC'] / p['H']
        if 0.08 <= gc_h_ratio <= 0.12:
            score += 10  # 运动化低重心
        
        # 长轴距奖励（内部空间优化）
        wb_ratio = p['WB'] / p['L']
        if wb_ratio >= 0.60:
            score += 10  # 长轴距设计
        
        # 宽轮距奖励（稳定性）
        tw_ratio = p['TW'] / p['W']
        if tw_ratio >= 0.84:
            score += 10  # 宽轮距设计
        
        # 大轮毂奖励（运动感）
        if p['WR'] >= 0.35:
            score += 5
        
        # A柱角度创新（更倾斜=更运动）
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
            'fwx': fwx, 'rwx': rwx, 'wcy': wcy,
            'hoodY': hoodY, 'waistY': waistY,
            'aTopX': aTopX, 'cTopX': cTopX,
            'cabinW': cabinW, 'frontFenderW': frontFenderW,
        }


# ============================================================
# 第二部分：遗传算法参数优化器
# ============================================================

class GeneticOptimizer:
    """遗传算法参数优化器"""
    
    # 参数范围约束
    PARAM_RANGES = {
        'L':  (3.5, 5.5),
        'W':  (1.4, 2.2),
        'H':  (1.1, 2.0),
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
            # 种子个体
            population.append(copy.deepcopy(seed_params))
            # 种子邻域个体
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
        # 按适应度排序
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
        
        # 评估
        evaluated = self.evaluate_population(population)
        
        # 记录最优
        best_ind, best_score, best_result = evaluated[0]
        if best_score > self.best_score_ever:
            self.best_score_ever = best_score
            self.best_ever = copy.deepcopy(best_ind)
        
        # 记录收敛历史
        avg_score = sum(s for _, s, _ in evaluated) / len(evaluated)
        self.convergence_history.append({
            'generation': self.generation,
            'best': best_score,
            'average': round(avg_score, 2),
            'best_ever': self.best_score_ever,
        })
        
        # 选择精英
        elites = self.select(evaluated)
        
        # 生成新一代
        new_population = list(elites)
        
        while len(new_population) < self.pop_size:
            # 选择父代
            p1 = random.choice(elites)
            p2 = random.choice(elites)
            
            if random.random() < self.crossover_rate:
                c1, c2 = self.crossover(p1, p2)
            else:
                c1, c2 = copy.deepcopy(p1), copy.deepcopy(p2)
            
            # 变异
            c1 = self._mutate(c1)
            c2 = self._mutate(c2)
            
            new_population.append(c1)
            if len(new_population) < self.pop_size:
                new_population.append(c2)
        
        return new_population, best_result, evaluated


# ============================================================
# 第三部分：迭代学习循环+收敛检测
# ============================================================

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
    
    def check_convergence(self):
        """收敛检测：最近N代最优分数变化小于阈值"""
        history = self.optimizer.convergence_history
        if len(history) < self.conv_window:
            return False
        
        recent = [h['best'] for h in history[-self.conv_window:]]
        variation = max(recent) - min(recent)
        return variation < self.conv_threshold
    
    def check_plateau(self):
        """平台检测：最优分数连续N代未提升"""
        history = self.optimizer.convergence_history
        if len(history) < self.patience:
            return False
        
        recent_best = [h['best_ever'] for h in history[-self.patience:]]
        return len(set(recent_best)) == 1  # 全部相同=未提升
    
    def learn(self, seed_params, callback=None):
        """执行迭代学习"""
        self.is_running = True
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
            
            # 收敛检测
            if self.check_convergence():
                gen_info['converged'] = True
                gen_info['convergence_reason'] = 'score_variation < threshold'
                break
            
            # 平台检测
            if self.check_plateau():
                # 增大变异率跳出局部最优
                self.optimizer.mutation_rate = min(0.4, self.optimizer.mutation_rate * 1.5)
                gen_info['plateau_detected'] = True
            
            # 每10代输出进度
            if (gen + 1) % 10 == 0:
                print(f"  Gen {gen+1}: best={best_result['total']:.1f} "
                      f"best_ever={self.optimizer.best_score_ever:.1f}")
        
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


# ============================================================
# 第四部分：智能涌现测试
# ============================================================

class EmergenceDetector:
    """智能涌现检测器"""
    
    def __init__(self):
        self.emergence_events = []
    
    def detect(self, history):
        """检测涌现事件"""
        if len(history) < 5:
            return []
        
        events = []
        
        # 1. 分数跃迁检测（单代提升>5分）
        for i in range(1, len(history)):
            prev_score = history[i-1].get('best_score', history[i-1].get('best', 0))
            curr_score = history[i].get('best_score', history[i].get('best', 0))
            delta = curr_score - prev_score
            if delta > 5:
                events.append({
                    'type': 'score_jump',
                    'generation': history[i]['generation'],
                    'delta': round(delta, 2),
                    'description': f"Gen {history[i]['generation']}: 分数跃迁 +{delta:.1f}",
                })
        
        # 2. 维度突破检测（某维度从<60突破到>80）
        if 'best_scores' in history[0]:
            dims = history[0]['best_scores'].keys()
            for dim in dims:
                for i in range(1, len(history)):
                    prev = history[i-1]['best_scores'].get(dim, 0)
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
        
        # 3. 收敛后突破检测（平台后再次提升）
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


# ============================================================
# 第五部分：主程序 - 25种车型自主学习
# ============================================================

# 25种车型种子参数
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

# 标杆数据
BENCHMARKS = {
    'sedan_c': {'L': 5.101, 'W': 1.987, 'H': 1.509, 'WB': 3.060, 'GC': 0.140},
    'sedan_d': {'L': 5.290, 'W': 1.921, 'H': 1.503, 'WB': 3.216, 'GC': 0.130},
    'suv_full': {'L': 5.060, 'W': 2.004, 'H': 1.779, 'WB': 3.105, 'GC': 0.220},
    'coupe': {'L': 4.519, 'W': 1.852, 'H': 1.298, 'WB': 2.450, 'GC': 0.120},
    'sports': {'L': 4.565, 'W': 1.958, 'H': 1.186, 'WB': 2.600, 'GC': 0.100},
    'mpv': {'L': 5.338, 'W': 1.978, 'H': 1.867, 'WB': 3.198, 'GC': 0.155},
}


def run_learning_session(model_key, seed_params, benchmark_data, 
                         generations=50, population=20):
    """运行单次学习会话"""
    print(f"\n{'='*60}")
    print(f"自主学习: {seed_params.get('name', model_key)}")
    print(f"标杆车型: {benchmark_data.get('name', 'N/A')}")
    print(f"{'='*60}")
    
    # 初始评估
    evaluator = SurfaceQualityEvaluator(benchmark_data)
    initial = evaluator.evaluate(seed_params)
    print(f"\n初始评分: {initial['total']:.1f}")
    for dim, score in initial['scores'].items():
        print(f"  {dim}: {score:.1f}")
    
    # 创建优化器
    optimizer = GeneticOptimizer(
        evaluator, 
        population_size=population,
        elite_ratio=0.2,
        mutation_rate=0.15,
        crossover_rate=0.7,
    )
    
    # 创建学习器
    learner = IterativeLearner(
        optimizer,
        max_generations=generations,
        convergence_window=10,
        convergence_threshold=0.5,
        patience=15,
    )
    
    # 执行学习
    params_copy = {k: v for k, v in seed_params.items() if k != 'name'}
    final = learner.learn(params_copy)
    
    # 涌现检测
    detector = EmergenceDetector()
    emergence = detector.detect(learner.results)
    
    # 最终评估
    final_eval = evaluator.evaluate(final['best_params'])
    
    print(f"\n最终评分: {final_eval['total']:.1f}")
    for dim, score in final_eval['scores'].items():
        print(f"  {dim}: {score:.1f}")
    print(f"提升: +{final_eval['total'] - initial['total']:.1f}")
    print(f"收敛代数: {final['total_generations']}")
    print(f"耗时: {final['elapsed']}s")
    
    if emergence:
        print(f"\n智能涌现事件 ({len(emergence)}):")
        for e in emergence:
            print(f"  ★ {e['description']}")
    
    return {
        'model_key': model_key,
        'initial_score': initial['total'],
        'final_score': final_eval['total'],
        'improvement': final_eval['total'] - initial['total'],
        'best_params': final['best_params'],
        'generations': final['total_generations'],
        'elapsed': final['elapsed'],
        'emergence_events': emergence,
        'convergence_history': final['convergence_history'],
    }


def main():
    """主程序：对所有车型运行自主学习"""
    print("=" * 70)
    print("EVOLUTION AI 自主学习引擎 v1.0")
    print("智能涌现：自动发现最优汽车造型参数")
    print("=" * 70)
    
    all_results = []
    
    for model_key, seed in SEED_MODELS.items():
        benchmark = BENCHMARKS.get(model_key, {})
        result = run_learning_session(
            model_key, seed, benchmark,
            generations=50, population=20,
        )
        all_results.append(result)
    
    # 汇总报告
    print(f"\n{'='*70}")
    print("自主学习汇总报告")
    print(f"{'='*70}")
    
    total_improvement = 0
    total_emergence = 0
    
    for r in all_results:
        name = SEED_MODELS[r['model_key']].get('name', r['model_key'])
        print(f"\n{name}:")
        print(f"  初始→最终: {r['initial_score']:.1f} → {r['final_score']:.1f} "
              f"(+{r['improvement']:.1f})")
        print(f"  收敛代数: {r['generations']}, 耗时: {r['elapsed']}s")
        print(f"  涌现事件: {len(r['emergence_events'])}")
        total_improvement += r['improvement']
        total_emergence += len(r['emergence_events'])
    
    print(f"\n总提升: +{total_improvement:.1f}")
    print(f"总涌现事件: {total_emergence}")
    
    # 保存结果
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'learning_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n结果已保存: {output_file}")
    
    # 生成最优参数报告
    print(f"\n{'='*70}")
    print("最优参数报告")
    print(f"{'='*70}")
    
    for r in all_results:
        name = SEED_MODELS[r['model_key']].get('name', r['model_key'])
        p = r['best_params']
        print(f"\n{name} (评分: {r['final_score']:.1f}):")
        print(f"  L={p['L']:.3f} W={p['W']:.3f} H={p['H']:.3f} WB={p['WB']:.3f}")
        print(f"  FO={p['FO']:.3f} RO={p['RO']:.3f} GC={p['GC']:.3f} WR={p['WR']:.3f}")
        print(f"  TW={p['TW']:.3f} AA={p['AA']:.1f} CA={p['CA']:.1f} WL={p['WL']:.3f}")


if __name__ == '__main__':
    main()