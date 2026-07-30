"""
AI Surface Quality Predictor (VLA - Vision-Language-Action)
Predicts automotive Class A surface quality from NURBS parameters

Architecture: Multi-layer Perceptron + Geometric Feature Extraction
"""
import json
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


# ============================================================
# Geometric Feature Extraction
# ============================================================

def extract_surface_features(surf_dict: dict) -> np.ndarray:
    """
    Extract geometric features from a NURBS surface dictionary
    
    Features:
    - Control point distribution statistics (mean, std, range of x,y,z)
    - Weight distribution statistics  
    - Degree information
    - Knot vector statistics
    - Aspect ratio
    - Surface complexity
    """
    cp = np.array(surf_dict['control_points'])  # Shape: (nu, nv, 3)
    w = np.array(surf_dict['weights'])           # Shape: (nu, nv)
    du = surf_dict['degree_u']
    dv = surf_dict['degree_v']
    ku = np.array(surf_dict['knots_u'])
    kv = np.array(surf_dict['knots_v'])
    
    features = []
    
    # --- Control Point Features ---
    # Position statistics
    features.extend([
        np.mean(cp[:,:,0]), np.std(cp[:,:,0]),  # X: mean, std
        np.min(cp[:,:,0]), np.max(cp[:,:,0]),
        np.mean(cp[:,:,1]), np.std(cp[:,:,1]),  # Y: mean, std
        np.min(cp[:,:,1]), np.max(cp[:,:,1]),
        np.mean(cp[:,:,2]), np.std(cp[:,:,2]),  # Z: mean, std
        np.min(cp[:,:,2]), np.max(cp[:,:,2]),
    ])
    
    # Aspect ratio of bounding box
    bbox_x = np.max(cp[:,:,0]) - np.min(cp[:,:,0])
    bbox_y = np.max(cp[:,:,1]) - np.min(cp[:,:,1])
    bbox_z = np.max(cp[:,:,2]) - np.min(cp[:,:,2])
    features.append(bbox_x / (bbox_y + 1e-8))
    features.append(bbox_y / (bbox_z + 1e-8))
    features.append(bbox_x / (bbox_z + 1e-8))
    
    # Control point grid shape
    nu, nv = cp.shape[:2]
    features.extend([nu, nv, nu / nv])
    
    # --- Weight Features ---
    features.extend([
        np.mean(w), np.std(w), np.min(w), np.max(w),
        np.sum(w > 1.0),    # Count of w > 1 (pulling in)
        np.sum(w < 1.0),    # Count of w < 1 (pushing out)
        np.sum(np.abs(w - 1.0) > 0.1),  # Non-uniform weights
    ])
    
    # Weight gradient (uniformity)
    w_diff_u = np.diff(w, axis=0)
    w_diff_v = np.diff(w, axis=1)
    features.extend([
        np.mean(np.abs(w_diff_u)),
        np.mean(np.abs(w_diff_v)),
        np.std(w_diff_u),
        np.std(w_diff_v),
    ])
    
    # --- Degree Features ---
    features.extend([du, dv, du * dv])
    
    # --- Knot Vector Features ---
    # Knot spacing uniformity
    ku_spacing = np.diff(ku)
    kv_spacing = np.diff(kv)
    features.extend([
        np.mean(ku_spacing), np.std(ku_spacing),
        np.mean(kv_spacing), np.std(kv_spacing),
        np.max(ku_spacing) / (np.min(ku_spacing) + 1e-8),  # Max/min ratio
        np.max(kv_spacing) / (np.min(kv_spacing) + 1e-8),
    ])
    
    # --- Complexity Features ---
    # Curvature of control polygon (approximate surface curvature)
    cp_du = np.diff(cp, axis=0)
    cp_dv = np.diff(cp, axis=1)
    features.extend([
        np.mean(np.linalg.norm(cp_du, axis=2)),
        np.mean(np.linalg.norm(cp_dv, axis=2)),
        np.std(np.linalg.norm(cp_du, axis=2)),
        np.std(np.linalg.norm(cp_dv, axis=2)),
    ])
    
    # Control net twist (magnitude of cross partials)
    cp_duv = np.diff(cp_du, axis=1)
    features.extend([
        np.mean(np.linalg.norm(cp_duv, axis=2)),
        np.std(np.linalg.norm(cp_duv, axis=2)),
        np.max(np.linalg.norm(cp_duv, axis=2)),
    ])
    
    # Diagonal ratio (should be close to 1 for well-proportioned surface)
    diag1 = np.linalg.norm(cp[-1,0] - cp[0,-1])
    diag2 = np.linalg.norm(cp[0,0] - cp[-1,-1])
    features.append(diag1 / (diag2 + 1e-8))
    
    return np.array(features, dtype=np.float64)


def extract_curve_features(curve_dict: dict) -> np.ndarray:
    """Extract features from a NURBS curve dictionary"""
    cp = np.array(curve_dict['control_points'])  # (n, 3)
    w = np.array(curve_dict['weights'])           # (n,)
    p = curve_dict['degree']
    knots = np.array(curve_dict['knots'])
    
    features = []
    
    # Position stats
    for dim in range(3):
        features.extend([np.mean(cp[:,dim]), np.std(cp[:,dim]),
                       np.min(cp[:,dim]), np.max(cp[:,dim])])
    
    # Length of control polygon
    cp_length = sum(np.linalg.norm(cp[i+1] - cp[i]) for i in range(len(cp)-1))
    features.append(cp_length)
    
    # Weight stats
    features.extend([np.mean(w), np.std(w), np.min(w), np.max(w),
                   np.sum(np.abs(w - 1.0) > 0.1)])
    
    # Degree
    features.append(p)
    
    # Knot spacing
    k_spacing = np.diff(knots)
    features.extend([np.mean(k_spacing), np.std(k_spacing),
                    np.max(k_spacing) / (np.min(k_spacing) + 1e-8)])
    
    return np.array(features, dtype=np.float64)


# ============================================================
# Surface VLA Model (Pure NumPy MLP)
# ============================================================

class SurfaceVLA:
    """
    Vision-Language-Action model for Surface Quality Prediction
    
    Architecture:
    - Input: Geometric feature vector (128 dims)
    - Hidden: 256 → 128 → 64 → 32
    - Output: Quality score (0-100) + Grade (A/B/C/Fail)
    
    Training: L2 regression on human-rated surface quality scores
    """
    
    def __init__(self, input_dim: int = 64, hidden_dims: List[int] = [256, 128, 64, 32]):
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.output_dim = 1
        
        # Initialize layers using Xavier/He initialization
        np.random.seed(42)
        
        self.weights = []
        self.biases = []
        
        dims = [input_dim] + hidden_dims + [self.output_dim]
        for i in range(len(dims) - 1):
            fan_in = dims[i]
            fan_out = dims[i + 1]
            scale = np.sqrt(2.0 / (fan_in + fan_out))
            W = np.random.randn(dims[i], dims[i+1]) * scale
            b = np.zeros(dims[i+1])
            self.weights.append(W)
            self.biases.append(b)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def relu_deriv(self, x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(float)
    
    def tanh(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x)
    
    def tanh_deriv(self, x: np.ndarray) -> np.ndarray:
        return 1.0 - np.tanh(x)**2
    
    def forward(self, X: np.ndarray, training: bool = True) -> Tuple[np.ndarray, List[np.ndarray]]:
        """
        Forward pass
        
        Args:
            X: Input features (batch_size, input_dim)
            
        Returns:
            (output, activations) — output shape: (batch_size, 1)
        """
        activations = [X]
        A = X
        
        for i in range(len(self.weights) - 1):
            Z = A @ self.weights[i] + self.biases[i]
            A = self.relu(Z)
            activations.append(A)
        
        # Output layer: linear
        output = A @ self.weights[-1] + self.biases[-1]
        activations.append(output)
        
        return output, activations
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict quality score"""
        output, _ = self.forward(X, training=False)
        # Sigmoid to [0, 1] then scale to [0, 100]
        return 100 * self.sigmoid(output)
    
    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    
    def predict_grade(self, X: np.ndarray) -> str:
        """Predict letter grade from features"""
        scores = self.predict(X)
        grades = []
        for score in scores:
            if score >= 85:
                grades.append('A')
            elif score >= 70:
                grades.append('B')
            elif score >= 50:
                grades.append('C')
            else:
                grades.append('Fail')
        return grades[0] if len(grades) == 1 else grades
    
    def train(self, X: np.ndarray, y: np.ndarray,
             epochs: int = 100, lr: float = 0.001,
             batch_size: int = 32) -> List[float]:
        """
        Train with SGD and L2 loss
        
        Args:
            X: Training features (n_samples, input_dim)
            y: Quality scores (n_samples,) in range [0, 100]
        """
        # Normalize targets to [0, 1]
        y_norm = y / 100.0
        
        losses = []
        n_samples = len(X_norm := np.array(X))
        
        for epoch in range(epochs):
            # Shuffle
            perm = np.random.permutation(n_samples)
            X_shuffled = X_norm[perm]
            y_shuffled = y_norm[perm]
            
            epoch_loss = 0.0
            n_batches = (n_samples + batch_size - 1) // batch_size
            
            for batch in range(n_batches):
                start = batch * batch_size
                end = min(start + batch_size, n_samples)
                
                X_batch = X_shuffled[start:end]
                y_batch = y_shuffled[start:end]
                
                # Forward
                output, activations = self.forward(X_batch, training=True)
                
                # L2 loss
                loss = np.mean((output.flatten() - y_batch)**2)
                epoch_loss += loss
                
                # Backward
                delta = output - y_batch.reshape(-1, 1)
                
                for i in range(len(self.weights) - 1, -1, -1):
                    grad_W = activations[i].T @ delta / len(X_batch)
                    grad_b = np.mean(delta, axis=0)
                    
                    # Gradient clipping
                    grad_W = np.clip(grad_W, -1.0, 1.0)
                    grad_b = np.clip(grad_b, -1.0, 1.0)
                    
                    self.weights[i] -= lr * grad_W
                    self.biases[i] -= lr * grad_b
                    
                    # Backprop delta
                    if i > 0:
                        delta = delta @ self.weights[i].T
                        delta = delta * self.relu_deriv(activations[i])
            
            avg_loss = epoch_loss / n_batches
            losses.append(avg_loss)
            
            if epoch % 20 == 0:
                preds = self.sigmoid(self.forward(X_norm, training=False)[0])
                train_acc = np.mean(np.abs(preds.flatten() * 100 - y_norm * 100) < 10)
                print(f"  Epoch {epoch:3d}: Loss={avg_loss:.4f}, MAE={train_acc*100:.1f}% within 10pts")
        
        return losses
    
    def save(self, path: str):
        """Save model weights"""
        data = {
            'weights': [w.tolist() for w in self.weights],
            'biases': [b.tolist() for b in self.biases],
            'input_dim': self.input_dim,
            'hidden_dims': self.hidden_dims
        }
        with open(path, 'w') as f:
            json.dump(data, f)
        print(f"✅ Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'SurfaceVLA':
        """Load model weights"""
        with open(path) as f:
            data = json.load(f)
        
        model = cls(input_dim=data['input_dim'], hidden_dims=data['hidden_dims'])
        model.weights = [np.array(w) for w in data['weights']]
        model.biases = [np.array(b) for b in data['biases']]
        print(f"✅ Model loaded from {path}")
        return model


# ============================================================
# Synthetic Training Data Generator
# ============================================================

def generate_synthetic_surface_dataset(n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic NURBS surface dataset with quality labels
    
    Quality labels based on:
    - Aspect ratio (closer to 1 = better)
    - Weight uniformity (closer to 1 = better)
    - Control net twist (lower = better)
    - Knot spacing uniformity (more uniform = better)
    """
    print(f"Generating {n_samples} synthetic surface samples...")
    
    surfaces = []
    labels = []
    
    for i in range(n_samples):
        # Random parameters
        nu = np.random.randint(3, 8)
        nv = np.random.randint(3, 8)
        du = np.random.randint(2, 4)
        dv = np.random.randint(2, 4)
        
        # Control points (random shape)
        cp = np.zeros((nu, nv, 3))
        for ii in range(nu):
            for jj in range(nv):
                cp[ii, jj] = np.array([
                    ii * np.random.uniform(0.5, 2.0) + np.random.uniform(-0.2, 0.2),
                    jj * np.random.uniform(0.5, 2.0) + np.random.uniform(-0.2, 0.2),
                    np.random.uniform(-0.5, 0.5)
                ])
        
        # Weights (biased toward 1 for better surfaces)
        if i < n_samples * 0.3:
            # Good surfaces: uniform weights
            w = np.ones((nu, nv)) + np.random.randn(nu, nv) * 0.05
        elif i < n_samples * 0.7:
            # Medium surfaces: slightly varying
            w = np.ones((nu, nv)) + np.random.randn(nu, nv) * 0.15
        else:
            # Poor surfaces: highly varying weights
            w = np.ones((nu, nv)) + np.random.randn(nu, nv) * 0.3
            w = np.clip(w, 0.3, 2.0)
        
        # Knot vectors
        import sys
        sys.path.insert(0, str(__file__).rsplit('/', 1)[0] + '/../core/geometry')
        from bsp import BSplineBasis
        ku = BSplineBasis.from_params(nu, du).knots.tolist()
        kv = BSplineBasis.from_params(nv, dv).knots.tolist()
        
        surf_dict = {
            'control_points': cp.tolist(),
            'weights': w.tolist(),
            'degree_u': du,
            'degree_v': dv,
            'knots_u': ku,
            'knots_v': kv
        }
        
        features = extract_surface_features(surf_dict)
        
        # Compute quality label
        # Good surfaces: aspect ratio close to 1, uniform weights, low twist
        bbox = cp.max(axis=(0,1)) - cp.min(axis=(0,1))
        aspect = bbox[0] / (bbox[1] + 1e-8)
        aspect_score = 1.0 - abs(aspect - 1.0) / 3.0
        
        w_score = 1.0 - np.std(w) * 3.0
        
        quality = 50 + aspect_score * 25 + w_score * 25
        quality = np.clip(quality, 0, 100)
        
        surfaces.append(features)
        labels.append(quality)
        
        if i % 200 == 0:
            print(f"  Generated {i}/{n_samples}...")
    
    return np.array(surfaces), np.array(labels)


# ============================================================
# Main: Train and Evaluate
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SURFACE VLA — AI Surface Quality Predictor")
    print("=" * 60)
    
    # Generate synthetic dataset
    X, y = generate_synthetic_surface_dataset(500)
    print(f"\nDataset shape: X={X.shape}, y={y.shape}")
    print(f"Quality range: {y.min():.1f} - {y.max():.1f}")
    
    # Ensure consistent feature dimension
    INPUT_DIM = min(X.shape[1], 64)  # Use first 64 features
    X = X[:, :INPUT_DIM]
    
    # Split
    n_train = int(0.8 * len(X))
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]
    
    print(f"\nTraining: {len(X_train)} samples")
    print(f"Test: {len(X_test)} samples")
    
    # Train model
    print("\n=== Training Surface VLA ===")
    model = SurfaceVLA(input_dim=INPUT_DIM, hidden_dims=[128, 64, 32])
    losses = model.train(X_train, y_train, epochs=150, lr=0.01, batch_size=32)
    
    # Evaluate
    print("\n=== Evaluation ===")
    preds = model.predict(X_test)
    
    mae = np.mean(np.abs(preds - y_test))
    rmse = np.sqrt(np.mean((preds - y_test)**2))
    
    print(f"Test MAE: {mae:.2f} points")
    print(f"Test RMSE: {rmse:.2f} points")
    
    # Grade prediction accuracy
    true_grades = []
    pred_grades = []
    for yt, yp in zip(y_test, preds):
        tg = 'A' if yt >= 85 else ('B' if yt >= 70 else ('C' if yt >= 50 else 'Fail'))
        pg = model.predict_grade(X_test[[list(y_test).index(yt)]])
        true_grades.append(tg)
        pred_grades.append(pg if isinstance(pg, str) else pg)
    
    grade_acc = np.mean([t == p for t, p in zip(true_grades, pred_grades)])
    print(f"Grade prediction accuracy: {grade_acc:.1%}")
    
    # Sample predictions
    print("\nSample predictions:")
    for i in range(min(10, len(X_test))):
        print(f"  True: {y_test[i]:.1f} ({true_grades[i]}) | Pred: {preds[i][0]:.1f} ({pred_grades[i]})")
    
    # Save model
    model.save("D:/API/EVO_AI/training/checkpoints/surface_vla.json")
    
    print("\n✅ Surface VLA training complete!")
