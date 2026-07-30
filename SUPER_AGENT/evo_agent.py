"""
EVOLUTION_AI — Automotive A-Surface SUPER_AGENT
Uses the SUPER_AGENT framework to orchestrate the automotive design system

Capabilities:
1. Design intent understanding (natural language → NURBS parameters)
2. Surface generation (parametric + AI)
3. Quality assessment (Class A validation)
4. Multi-objective optimization (form + aerodynamics + manufacturing)
5. Iterative refinement (closed-loop improvement)
"""
import sys
import os
import json
import time
import re
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# Add EVO_AI to path
EVO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EVO_ROOT))
sys.path.insert(0, str(EVO_ROOT / "core"))
sys.path.insert(0, str(EVO_ROOT / "generation"))

from core.nurbs.surface import NURBSSurface
from core.nurbs.curve import NURBSCurve
from core.nurbs.continuity import compute_surface_quality_score, analyze_edge_continuity


# ============================================================
# Design Intent Parser
# ============================================================

@dataclass
class DesignIntent:
    """Parsed design intent from natural language"""
    part_type: str           # 'hood', 'door', 'wheel', 'bumper', etc.
    style: str               # 'sporty', 'luxury', 'minimal', 'aggressive'
    curvature: str           # 'flat', 'gentle', 'sweeping', 'complex'
    keywords: List[str]      # Extracted keywords
    constraints: Dict[str, Any]  # Size, position constraints
    
    # Aesthetic descriptors
    has_fastback: bool = False
    has_tear_drop: bool = False
    has_muscle_lines: bool = False
    has_zero_ship: bool = False  # Side window zero-gap
    has_flush_handles: bool = False
    has_breathing_hood: bool = False
    
    def __str__(self):
        return f"DesignIntent({self.part_type}, {self.style}, curvature={self.curvature})"


class DesignIntentParser:
    """
    Parse natural language design intent into structured parameters
    """
    
    # Style keywords
    STYLE_KEYWORDS = {
        'sporty': ['sport', 'aggressive', 'dynamic', 'fast', 'racing', 'muscular', 'athletic'],
        'luxury': ['luxury', 'elegant', 'refined', 'premium', 'sophisticated', 'executive'],
        'minimal': ['minimal', 'clean', 'simple', 'stripped', 'pure', 'essential'],
        'futuristic': ['future', 'tech', 'cyber', 'innovative', 'ev', 'electric'],
    }
    
    CURVATURE_KEYWORDS = {
        'flat': ['flat', 'planar', 'flush', 'clean'],
        'gentle': ['gentle', 'smooth', 'flowing', 'organic', 'soft'],
        'sweeping': ['sweeping', 'long', 'fluid', 'coupe', 'fastback'],
        'complex': ['complex', 'sculpted', 'muscular', 'tensioned', 'characteristic'],
    }
    
    PART_KEYWORDS = {
        'hood': ['hood', 'bonnet', 'engine cover', 'engine lid'],
        'fender': ['fender', 'wing', 'wheel arch', 'quarter panel'],
        'door': ['door', 'door panel'],
        'roof': ['roof', 'roofline', 'coupe roof'],
        'trunk': ['trunk', 'boot', 'rear lid', 'tailgate'],
        'bumper': ['bumper', 'front bumper', 'rear bumper', 'skirt'],
        'grille': ['grille', 'grill', 'front face', 'mask'],
        'headlight': ['headlight', 'lamp', 'DRL', 'lighting'],
        'wheel': ['wheel', 'rim', 'alloy', 'wheel design'],
        'mirror': ['mirror', 'wing mirror', 'side mirror'],
        'side_skirt': ['side skirt', 'skirt', 'sill'],
        'spoiler': ['spoiler', 'wing', 'rear wing', 'lip'],
        'body_side': ['body side', 'door panel', 'fender'],
    }
    
    FEATURE_KEYWORDS = {
        'has_fastback': ['fastback', 'fast back', 'sloping roof'],
        'has_tear_drop': ['tear drop', 'teardrop', 'aero profile'],
        'has_muscle_lines': ['muscle line', 'character line', 'shoulder line', 'haunch'],
        'has_zero_ship': ['zero gap', 'zero-gap', 'flush glass'],
        'has_flush_handles': ['flush handle', 'pop-out handle', 'hidden handle'],
        'has_breathing_hood': ['breathing hood', 'power dome', 'bulge'],
    }
    
    def parse(self, text: str) -> DesignIntent:
        """Parse natural language design intent"""
        text_lower = text.lower()
        
        # Extract part type
        part_type = 'body_side'
        for part, keywords in self.PART_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                part_type = part
                break
        
        # Extract style
        style = 'minimal'
        for s, keywords in self.STYLE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                style = s
                break
        
        # Extract curvature
        curvature = 'gentle'
        for c, keywords in self.CURVATURE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                curvature = c
                break
        
        # Extract features
        features = {}
        for feat, keywords in self.FEATURE_KEYWORDS.items():
            features[feat] = any(kw in text_lower for kw in keywords)
        
        # Extract constraints (numbers)
        constraints = {}
        numbers = re.findall(r'(\d+\.?\d*)\s*(mm|cm|m|inch|degrees?|°)', text_lower)
        for num, unit in numbers:
            constraints[unit] = float(num)
        
        return DesignIntent(
            part_type=part_type,
            style=style,
            curvature=curvature,
            keywords=[style, curvature, part_type],
            constraints=constraints,
            **features
        )


# ============================================================
# Surface Generator
# ============================================================

class SurfaceGenerator:
    """
    Generate NURBS automotive surfaces from design intent
    
    Parameters vary by style and curvature:
    - Sporty: Higher curvature, sharper transitions, lower roof
    - Luxury: Gentle curves, smooth continuous surfaces, higher roof
    - Minimal: Flat panels, sharp edges, flush surfaces
    """
    
    def generate(self, intent: DesignIntent) -> NURBSSurface:
        """Generate surface based on design intent"""
        
        generators = {
            'hood': self._generate_hood,
            'fender': self._generate_fender,
            'door': self._generate_door,
            'roof': self._generate_roof,
            'trunk': self._generate_trunk,
            'bumper': self._generate_bumper,
            'body_side': self._generate_body_side,
            'wheel': self._generate_wheel,
            'mirror': self._generate_mirror,
            'spoiler': self._generate_spoiler,
        }
        
        gen = generators.get(intent.part_type, self._generate_body_side)
        return gen(intent)
    
    def _generate_hood(self, intent: DesignIntent) -> NURBSSurface:
        """Generate hood/bonnet surface"""
        # Style parameters
        params = self._get_style_params(intent.style, intent.curvature)
        
        # Control point grid: 5x4 for hood
        nu, nv = 5, 4
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        # Hood dimensions (typical sedan)
        length = params.get('hood_length', 1.8)   # m
        width = params.get('hood_width', 1.4)    # m
        bow_height = params.get('bow_height', 0.08)  # Power dome height
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Height profile (Z)
                # Primary bow (power dome)
                z = bow_height * 4 * u * (1 - u) * 4 * v * (1 - v)
                
                # Secondary crease (character line along length)
                crease_z = 0.03 * np.sin(u * np.pi) * np.exp(-((v - 0.5)**2) / 0.05)
                z += crease_z
                
                # Side taper (lower at edges)
                edge_taper = -0.02 * np.sin(v * np.pi)
                z += edge_taper
                
                # Sporty: add hood vents/bulges
                if intent.style == 'sporty' and v < 0.3:
                    vent_bulge = 0.02 * np.sin(u * np.pi * 3) * (1 - v / 0.3)
                    z += vent_bulge
                
                cp[i, j] = np.array([x, y, z])
                
                # Weight adjustment for curvature
                if abs(z) > bow_height * 0.5:
                    w[i, j] = 0.85  # Pull inward for sharper curves
        
        # Generate knot vectors
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_fender(self, intent: DesignIntent) -> NURBSSurface:
        """Generate fender/wheel arch surface"""
        nu, nv = 5, 5
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 1.2  # Wheelbase length
        width = 1.0  # Fender width
        arch_depth = 0.1  # Wheel arch depth
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Wheel arch (Gaussian bump)
                arch_x = 0.5  # Center of arch
                arch_r = 0.3  # Arch radius
                
                dist = np.sqrt((u - arch_x)**2 + (v - 0.5)**2)
                arch_z = arch_depth * np.exp(-dist**2 / (2 * (arch_r/2)**2))
                
                # Fender surface continues around arch
                z = arch_z
                
                # Muscle lines for sporty
                if intent.style == 'sporty' and intent.has_muscle_lines:
                    z += 0.015 * np.sin(u * np.pi * 2)
                
                cp[i, j] = np.array([x, y, z])
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_body_side(self, intent: DesignIntent) -> NURBSSurface:
        """Generate complete body side surface"""
        nu, nv = 6, 5
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 4.5   # Vehicle length
        height = 1.4   # Body height
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                z = (v - 0.5) * height
                
                # Body side profile (Y direction)
                # Typical sedan silhouette
                y_base = 0.0
                
                # Roof line (for fastback/sloping roof)
                if intent.has_fastback and u > 0.4:
                    roof_drop = (u - 0.4) * 0.3  # Fastback drop
                    if z > 0.1:  # Only affect upper body
                        z -= roof_drop
                
                # Character line
                char_line_z = 0.15  # Mid-body height
                char_line = 0.012 * np.exp(-((v - char_line_z / height - 0.5)**2) / 0.02)
                
                # Muscle line
                if intent.has_muscle_lines:
                    char_line += 0.01 * np.sin(u * np.pi * 4)
                
                z += char_line
                
                cp[i, j] = np.array([x, y_base, z])
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_wheel(self, intent: DesignIntent) -> NURBSSurface:
        """Generate wheel rim surface"""
        # Use revolution of a profile curve
        from core.nurbs.curve import NURBSCurve
        
        # Profile: wheel rim cross-section
        profile_pts = [
            np.array([0.30, 0.0, 0.0]),   # Inner hub
            np.array([0.30, 0.05, 0.0]),  # Hub edge
            np.array([0.32, 0.08, 0.0]),  # Rim start
            np.array([0.32, 0.20, 0.0]),  # Rim face
            np.array([0.30, 0.22, 0.0]),   # Rim lip
            np.array([0.30, 0.25, 0.0]),   # Outer edge
            np.array([0.30, 0.28, 0.0]),   # Tire start
            np.array([0.30, 0.32, 0.0]),  # Tire outer
            np.array([0.30, 0.35, 0.0]),  # Tire edge
        ]
        
        profile = NURBSCurve.interpolate(profile_pts, degree=3)
        
        # Revolution around Y axis
        return NURBSSurface.create_revolution(profile, axis=(0, 1, 0), 
                                             center=(0, 0.15, 0), num_sections=12)
    
    def _generate_roof(self, intent: DesignIntent) -> NURBSSurface:
        """Generate roof surface"""
        nu, nv = 5, 4
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 3.5
        width = 1.2
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Roof crown (gentle curve, like a tent)
                z = 0.02 * np.sin(u * np.pi) * np.sin(v * np.pi)
                
                # Fastback slope at rear
                if intent.has_fastback and u > 0.5:
                    slope = (u - 0.5) * 0.2
                    z -= slope * abs(v - 0.5) * 2
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_spoiler(self, intent: DesignIntent) -> NURBSSurface:
        """Generate rear spoiler/wing surface"""
        nu, nv = 4, 3
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 1.0
        width = 0.15  # Thin wing
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Wing profile (NACA airfoil-ish)
                if j == 1:  # Upper surface
                    z = 0.03 * np.sin(u * np.pi) * 4 * u * (1 - u)
                elif j == 2:  # Lower surface
                    z = 0.01 * np.sin(u * np.pi)
                else:
                    z = 0
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_bumper(self, intent: DesignIntent) -> NURBSSurface:
        """Generate bumper surface"""
        nu, nv = 5, 4
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 0.3  # Bumper depth
        width = 1.6
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Bumper curvature (bulge toward grille)
                z = 0.05 * np.sin(u * np.pi) * np.sin(v * np.pi)
                
                # Air intake recess
                if 0.3 < u < 0.7 and 0.3 < v < 0.7:
                    recess = 0.02 * np.sin((u - 0.3) / 0.4 * np.pi) * \
                             np.sin((v - 0.3) / 0.4 * np.pi)
                    z -= recess
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_door(self, intent: DesignIntent) -> NURBSSurface:
        """Generate door panel surface"""
        return self._generate_body_side(intent)  # Simplified
    
    def _generate_trunk(self, intent: DesignIntent) -> NURBSSurface:
        """Generate trunk lid surface"""
        nu, nv = 5, 4
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        length = 1.0
        width = 1.3
        
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                x = u * length
                y = (v - 0.5) * width
                
                # Slight curvature
                z = 0.015 * np.sin(u * np.pi) * np.sin(v * np.pi)
                
                if intent.has_fastback:
                    z -= 0.1 * u
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _generate_mirror(self, intent: DesignIntent) -> NURBSSurface:
        """Generate side mirror surface"""
        nu, nv = 4, 3
        cp = np.zeros((nu, nv, 3))
        w = np.ones((nu, nv))
        
        # Teardrop mirror shape
        for i in range(nu):
            u = i / (nu - 1)
            for j in range(nv):
                v = j / (nv - 1)
                
                # Teardrop profile
                x = u * 0.15
                y = (v - 0.5) * 0.12
                z = 0.02 * np.sin(u * np.pi) * np.sin(v * np.pi)
                
                cp[i, j] = np.array([x, y, z])
        
        from core.geometry.bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, 3).knots.tolist()
        kv = BSplineBasis.from_params(nv, 3).knots.tolist()
        
        return NURBSSurface(cp, w, 3, 3, ku, kv)
    
    def _get_style_params(self, style: str, curvature: str) -> dict:
        """Get generation parameters based on style"""
        params = {
            'hood_length': 1.8,
            'hood_width': 1.4,
            'bow_height': 0.06,
        }
        
        if style == 'sporty':
            params.update({
                'bow_height': 0.10,
                'crease_depth': 0.03,
                'surface_tension': 0.8,
            })
        elif style == 'luxury':
            params.update({
                'bow_height': 0.03,
                'crease_depth': 0.01,
                'surface_tension': 0.3,
            })
        elif style == 'minimal':
            params.update({
                'bow_height': 0.01,
                'crease_depth': 0.005,
                'surface_tension': 0.5,
            })
        
        return params


# ============================================================
# EVOLUTION AI Agent
# ============================================================

class EvoAgent:
    """
    Main EVOLUTION AI Agent
    
    Design flow:
    1. Parse intent (自然语言 → 结构化参数)
    2. Generate surface (参数 → NURBS 曲面)
    3. Assess quality (Class A 评估)
    4. Optimize (多目标优化)
    5. Report (结果输出)
    """
    
    def __init__(self):
        self.intent_parser = DesignIntentParser()
        self.surface_generator = SurfaceGenerator()
        self.history = []
        
        print("=" * 60)
        print("EVOLUTION_AI Agent Initialized")
        print("Automotive Class A Surface Design System")
        print("=" * 60)
    
    def run(self, design_request: str) -> dict:
        """
        Process a design request end-to-end
        
        Args:
            design_request: Natural language design description
            
        Returns:
            Dictionary with generated surface, quality score, and analysis
        """
        print(f"\n{'='*60}")
        print(f"Processing: {design_request}")
        print(f"{'='*60}")
        
        step_start = time.time()
        
        # Step 1: Parse intent
        intent = self.intent_parser.parse(design_request)
        print(f"\n📋 Intent parsed:")
        print(f"   Part: {intent.part_type}")
        print(f"   Style: {intent.style}")
        print(f"   Curvature: {intent.curvature}")
        print(f"   Features: {[k for k, v in intent.__dict__.items() if v is True and k.startswith('has_')]}")
        
        # Step 2: Generate surface
        print(f"\n⚙️  Generating NURBS surface...")
        gen_start = time.time()
        surface = self.surface_generator.generate(intent)
        gen_time = time.time() - gen_start
        print(f"   Generated in {gen_time*1000:.1f}ms")
        print(f"   Control points: {surface.control_points.shape}")
        print(f"   Degree: {surface.degree_u}x{surface.degree_v}")
        
        # Step 3: Assess quality
        print(f"\n🔍 Class A Surface Assessment...")
        assess_start = time.time()
        surf_dict = surface.to_dict()
        quality = compute_surface_quality_score(surface, nu_samples=20, nv_samples=20)
        assess_time = time.time() - assess_start
        
        print(f"   Overall Score: {quality['overall_score']:.1f} / 100")
        print(f"   Grade: {quality['grade']}")
        print(f"   Curvature Smoothness: {quality['curvature_smoothness']:.6f}")
        print(f"   Min Radius: {quality['min_curvature_radius']:.4f}m")
        print(f"   Assessed in {assess_time*1000:.1f}ms")
        
        total_time = time.time() - step_start
        
        # Step 4: Compile result
        result = {
            'design_request': design_request,
            'intent': {
                'part_type': intent.part_type,
                'style': intent.style,
                'curvature': intent.curvature,
                'features': {k: v for k, v in intent.__dict__.items() 
                           if k not in ['keywords', 'constraints']}
            },
            'surface': surf_dict,
            'quality': quality,
            'timing': {
                'total_ms': total_time * 1000,
                'generation_ms': gen_time * 1000,
                'assessment_ms': assess_time * 1000,
            }
        }
        
        self.history.append(result)
        
        print(f"\n✅ Complete in {total_time*1000:.1f}ms")
        return result
    
    def batch_run(self, requests: List[str]) -> List[dict]:
        """Process multiple design requests"""
        results = []
        for req in requests:
            result = self.run(req)
            results.append(result)
        return results
    
    def compare(self, results: List[dict]) -> dict:
        """Compare multiple design results"""
        scores = [r['quality']['overall_score'] for r in results]
        grades = [r['quality']['grade'] for r in results]
        
        best_idx = scores.index(max(scores))
        
        return {
            'best_index': best_idx,
            'best_score': scores[best_idx],
            'best_grade': grades[best_idx],
            'scores': scores,
            'average_score': sum(scores) / len(scores),
        }


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='EVOLUTION_AI Agent')
    parser.add_argument('--request', '-r', type=str, 
                       help='Design request in natural language')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode')
    args = parser.parse_args()
    
    agent = EvoAgent()
    
    if args.interactive:
        print("\n🎨 Interactive Mode — Enter design requests (or 'quit' to exit)")
        while True:
            req = input("\nDesign request: ")
            if req.lower() in ['quit', 'exit', 'q']:
                break
            if not req.strip():
                continue
            result = agent.run(req)
            print(f"\n📊 Quality: {result['quality']['grade']} ({result['quality']['overall_score']:.1f}/100)")
    
    elif args.request:
        result = agent.run(args.request)
        print(f"\n📊 Quality: {result['quality']['grade']} ({result['quality']['overall_score']:.1f}/100)")
    
    else:
        # Demo: Run standard examples
        print("\n🎨 Running Demo Examples...\n")
        
        examples = [
            "Design a sporty hood with breathing bulge and sharp character lines",
            "Create a luxury door panel with gentle flowing surfaces",
            "Generate a fastback roof with tear drop profile",
            "Design a muscle car fender with muscular haunches",
            "Create a flush rear spoiler with NACA airfoil profile",
        ]
        
        results = agent.batch_run(examples)
        
        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        comparison = agent.compare(results)
        
        for i, (req, result) in enumerate(zip(examples, results)):
            grade = result['quality']['grade']
            score = result['quality']['overall_score']
            part = result['intent']['part_type']
            style = result['intent']['style']
            marker = "🏆" if i == comparison['best_index'] else "  "
            print(f"{marker} #{i+1} [{part}/{style}] Score={score:.1f} Grade={grade}")
        
        print(f"\n🏆 Best: Example #{comparison['best_index']+1} ({comparison['best_score']:.1f})")
        
        # Save results
        output_path = EVO_ROOT / "logs" / f"evo_results_{int(time.time())}.json"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({'results': results, 'comparison': comparison}, f, indent=2)
        print(f"\n💾 Results saved to {output_path}")
