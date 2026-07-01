import os
import json
import trimesh
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from app.config.settings import settings
from app.core.workflow_engine import WorkflowStep
from app.utils.logger import logger


class TopologyOptimizer:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        return {
            'target_faces': settings.TOPOLOGY_TARGET_FACES,
            'quad_ratio_threshold': 0.80,
            'min_quad_ratio': settings.TOPOLOGY_MIN_QUAD_RATIO,
            'max_boundary_edges': 100,
            'fix_normals': True,
            'merge_vertices': True,
            'remove_duplicates': True,
            'export_format': 'obj',
            'quality_check': True
        }

    def load_mesh(self, file_path: str) -> trimesh.Trimesh:
        try:
            mesh = trimesh.load(file_path, force='mesh')

            if isinstance(mesh, trimesh.Scene):
                geometries = list(mesh.geometry.values())
                if geometries:
                    mesh = geometries[0]
                else:
                    raise ValueError("Scene contains no geometries")

            logger.info(f"Loaded mesh: {len(mesh.faces)} faces, {len(mesh.vertices)} vertices")
            return mesh

        except Exception as e:
            raise Exception(f"Failed to load model: {str(e)}")

    def preprocess_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        if self.config['fix_normals']:
            mesh.fix_normals()
            logger.info("Fixed normals")

        if self.config['merge_vertices']:
            mesh.merge_vertices()
            logger.info("Merged vertices")

        if self.config['remove_duplicates']:
            mesh.remove_duplicate_faces()
            logger.info("Removed duplicate faces")

        mesh.remove_infinite_values()
        mesh.remove_unreferenced_vertices()

        return mesh

    def optimize_topology(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        target_faces = self.config['target_faces']
        current_faces = len(mesh.faces)

        if current_faces > target_faces:
            ratio = target_faces / current_faces
            simplified = mesh.simplify_quadratic_decimation(target_faces)
            logger.info(f"Simplified mesh: {current_faces} → {len(simplified.faces)} faces")
            mesh = simplified
        else:
            logger.info(f"Face count already meets requirement: {current_faces}")

        return mesh

    def quality_check(self, mesh: trimesh.Trimesh, filename: str) -> Dict[str, Any]:
        result = {
            'filename': filename,
            'num_faces': len(mesh.faces),
            'num_vertices': len(mesh.vertices),
            'quad_ratio': 0.0,
            'boundary_edges': 0,
            'is_watertight': False,
            'issues': []
        }

        quad_count = sum(1 for face in mesh.faces if len(face) == 4)
        result['quad_ratio'] = quad_count / len(mesh.faces) if len(mesh.faces) > 0 else 0
        logger.info(f"Quad ratio: {result['quad_ratio']:.2%}")

        if result['quad_ratio'] < self.config['min_quad_ratio']:
            result['issues'].append(
                f"Quad ratio too low: {result['quad_ratio']:.2%} < {self.config['min_quad_ratio']:.2%}"
            )

        result['boundary_edges'] = len(mesh.boundary_edges)
        logger.info(f"Boundary edges: {result['boundary_edges']}")

        if result['boundary_edges'] > self.config['max_boundary_edges']:
            result['issues'].append(
                f"Too many boundary edges: {result['boundary_edges']} > {self.config['max_boundary_edges']}"
            )

        result['is_watertight'] = mesh.is_watertight
        logger.info(f"Watertight: {'Yes' if result['is_watertight'] else 'No'}")

        if not result['is_watertight']:
            result['issues'].append("Mesh is not watertight, contains holes")

        return result

    def export_mesh(self, mesh: trimesh.Trimesh, input_file: str) -> str:
        input_path = Path(input_file)
        output_filename = input_path.stem + '.' + self.config['export_format']
        output_path = settings.exports_path / output_filename

        mesh.export(str(output_path))
        logger.info(f"Exported to: {output_path}")

        return str(output_path)

    def process(self, input_file: str) -> Dict[str, Any]:
        logger.info(f"Starting topology optimization for: {input_file}")

        mesh = self.load_mesh(input_file)
        mesh = self.preprocess_mesh(mesh)
        optimized_mesh = self.optimize_topology(mesh)

        quality_result = None
        if self.config['quality_check']:
            quality_result = self.quality_check(optimized_mesh, Path(input_file).name)

        output_file = self.export_mesh(optimized_mesh, input_file)

        return {
            'input_file': input_file,
            'output_file': output_file,
            'original_faces': len(mesh.faces),
            'optimized_faces': len(optimized_mesh.faces),
            'quality_result': quality_result,
            'timestamp': datetime.now().isoformat()
        }


class TopologyOptimizationStep(WorkflowStep):
    def __init__(self, input_file: str, config: Optional[Dict] = None):
        super().__init__("Topology Optimization", "optimization")
        self.input_file = input_file
        self.optimizer = TopologyOptimizer(config)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self.optimizer.process(self.input_file)
        return result