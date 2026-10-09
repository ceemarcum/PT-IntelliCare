"""
Export the autoencoder's weights from the Keras file to a plain NumPy file, so the backend
can run the model without TensorFlow (Windows Smart App Control blocks TensorFlow's DLLs).

Run this again whenever you retrain the model in preprocess.ipynb:
    py -m autoencoder.export_weights

It only needs h5py (no TensorFlow). Reads recovery_autoencoder.weights.h5, writes recovery_autoencoder_weights.npz.
"""
from pathlib import Path

import h5py
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
H5_PATH = MODEL_DIR / "recovery_autoencoder.weights.h5"
NPZ_PATH = MODEL_DIR / "recovery_autoencoder_weights.npz"

# Layer order in the AnomalyDetector class: encoder (3 -> 4 -> 2), then decoder (2 -> 4 -> 3)
LAYERS = ["encoder/layers/dense", "encoder/layers/dense_1", "decoder/layers/dense", "decoder/layers/dense_1"]


def export():
    arrays = {}
    with h5py.File(H5_PATH, "r") as f:
        for i, name in enumerate(LAYERS):
            arrays[f"W{i}"] = np.array(f[f"{name}/vars/0"])   # weights
            arrays[f"b{i}"] = np.array(f[f"{name}/vars/1"])   # biases
    np.savez(NPZ_PATH, **arrays)
    print(f"Saved {NPZ_PATH.name}: " + ", ".join(f"{k} {v.shape}" for k, v in arrays.items()))


if __name__ == "__main__":
    export()
