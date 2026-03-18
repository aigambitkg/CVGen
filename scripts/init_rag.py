#!/usr/bin/env python3
"""
CVGen RAG Initialization Script
Initializes Qdrant with QPanda3 documentation for Retrieval Augmented Generation
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Optional

try:
    import requests
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    print(f"Error: Required package not found. {e}")
    print("Install with: pip install requests qdrant-client")
    exit(1)


class RAGInitializer:
    """Initialize Qdrant with QPanda3 documentation"""

    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "cvgen_qpanda3")
        self.docs_dir = Path("/app/data/qpanda3_docs")
        self.vector_dim = 384  # For small embeddings
        self.client: Optional[QdrantClient] = None

    def connect(self) -> bool:
        """Connect to Qdrant"""
        try:
            print(f"Connecting to Qdrant at {self.qdrant_url}...")
            self.client = QdrantClient(url=self.qdrant_url, timeout=10)

            # Verify connection
            health = self.client.get_collection(self.collection_name)
            print(f"  ✓ Connected to existing collection: {self.collection_name}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                print(f"  Collection does not exist, will create...")
                return self._create_collection()
            else:
                print(f"  Error connecting: {e}")
                return False

    def _create_collection(self) -> bool:
        """Create the collection if it doesn't exist"""
        try:
            print(f"Creating collection: {self.collection_name}")
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_dim, distance=Distance.COSINE),
            )
            print(f"  ✓ Collection created successfully")
            return True
        except Exception as e:
            print(f"  Error creating collection: {e}")
            return False

    def _generate_simple_embedding(self, text: str) -> list:
        """Generate a simple embedding using hash-based approach"""
        # This is a fallback when proper embeddings aren't available
        # In production, use proper embedding models
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert hash to embedding vector
        embedding = []
        for i in range(0, len(hash_hex), 8):
            chunk = hash_hex[i : i + 8]
            value = float(int(chunk, 16)) / 0xFFFFFFFF
            embedding.append(value * 2 - 1)  # Normalize to [-1, 1]

        # Pad or truncate to desired dimension
        while len(embedding) < self.vector_dim:
            embedding.append(0.0)
        return embedding[: self.vector_dim]

    def _load_documents(self) -> list:
        """Load QPanda3 documentation from bundled files"""
        documents = []

        # Default bundled documents
        bundled_docs = {
            "qpanda3_api_reference": """
QPanda3 API Reference - Quantum Programming Framework

## Basic Gate Functions

### Single Qubit Gates
- H(qubit): Hadamard gate - creates superposition
- X(qubit): Pauli-X gate (NOT) - flips qubit
- Y(qubit): Pauli-Y gate - rotation around Y-axis
- Z(qubit): Pauli-Z gate - phase flip
- S(qubit): Phase gate - adds π/2 phase
- T(qubit): T gate - adds π/4 phase
- RX(qubit, angle): X-axis rotation
- RY(qubit, angle): Y-axis rotation
- RZ(qubit, angle): Z-axis rotation

### Multi-Qubit Gates
- CNOT(control, target): Controlled NOT
- CZ(control, target): Controlled Z
- SWAP(qubit1, qubit2): Swap qubits
- Toffoli(control1, control2, target): Controlled CNOT

## Circuit Creation and Execution
- create_empty_qprog(): Create empty quantum program
- cq_program(): Construct quantum circuit
- measure(qubit, classical_bit): Measure qubit
- run(circuit, backend): Execute circuit
""",
            "qpanda3_examples_bell": """
Bell State Example - Quantum Entanglement

Bell states demonstrate quantum entanglement - the key resource for quantum computing.

Example: Creating a Bell state (00+11)/√2

```python
from qpanda3 import *

# Create quantum program
prog = cq_program()
qbits = prog.allocate_qubits(2)
cbits = prog.allocate_cbits(2)

# Create Bell state
prog << H(qbits[0])
prog << CNOT(qbits[0], qbits[1])

# Measure both qubits
prog << measure(qbits, cbits)

# Run on simulator
result = run(prog, "qsim")
print(result.get_counts())
# Output: {'00': 500, '11': 500} (for 1000 shots)
```

This creates maximum entanglement between two qubits.
""",
            "qpanda3_examples_grover": """
Grover's Algorithm - Quantum Search

Grover's algorithm provides quadratic speedup for unstructured search.

Example: Search for marked element

```python
from qpanda3 import *

def oracle(prog, marked_state):
    '''Oracle marks the solution state'''
    # Flip phase of marked state
    qbits = prog.get_qubits()
    prog << X(qbits[-1])
    prog << H(qbits[-1])
    # Multi-controlled Z gate
    prog << Z(qbits[0])  # Simplified
    prog << H(qbits[-1])
    prog << X(qbits[-1])

def diffusion_operator(prog):
    '''Amplitude amplification'''
    qbits = prog.get_qubits()
    for q in qbits:
        prog << H(q)
        prog << X(q)
    prog << Z(qbits[0])
    for q in qbits:
        prog << X(q)
        prog << H(q)

# Setup
prog = cq_program()
qbits = prog.allocate_qubits(3)
cbits = prog.allocate_cbits(3)

# Initialize superposition
for q in qbits:
    prog << H(q)

# Grover iterations (≈ π/4 * √N)
for _ in range(2):  # Optimal for 3 qubits
    oracle(prog, 5)
    diffusion_operator(prog)

# Measure
prog << measure(qbits, cbits)
result = run(prog, "qsim")
```
""",
            "qpanda3_examples_vqe": """
Variational Quantum Eigensolver (VQE)

VQE is a hybrid quantum-classical algorithm for finding ground states.

Example: Simple VQE circuit

```python
from qpanda3 import *
import numpy as np

def vqe_circuit(params):
    '''Parameterized quantum circuit'''
    prog = cq_program()
    qbits = prog.allocate_qubits(2)
    cbits = prog.allocate_cbits(2)

    # Initial state
    prog << H(qbits[0])
    prog << H(qbits[1])

    # Parameterized gates
    prog << RZ(qbits[0], params[0])
    prog << RY(qbits[0], params[1])
    prog << RZ(qbits[1], params[2])
    prog << RY(qbits[1], params[3])

    # Entangling layer
    prog << CNOT(qbits[0], qbits[1])

    # Measurement
    prog << measure(qbits, cbits)

    return prog

def measure_expectation(params):
    '''Classical optimization'''
    prog = vqe_circuit(params)
    result = run(prog, "qsim", shots=1000)
    # Calculate expectation value
    counts = result.get_counts()
    expectation = 0
    for state, count in counts.items():
        energy_contribution = int(state[0]) - int(state[1])
        expectation += energy_contribution * count / 1000
    return expectation

# Classical optimization loop
initial_params = np.random.random(4)
# Use scipy.optimize.minimize with measure_expectation as objective
```
""",
            "qpanda3_examples_qml": """
Quantum Machine Learning

Quantum circuits can be used as feature maps and ansätze for ML.

Example: Quantum Neural Network layer

```python
from qpanda3 import *
import numpy as np

def quantum_feature_map(data):
    '''Encode classical data into quantum state'''
    prog = cq_program()
    qbits = prog.allocate_qubits(len(data))

    for i, x in enumerate(data):
        prog << RY(qbits[i], x)

    return prog

def ansatz_circuit(weights):
    '''Trainable quantum circuit'''
    prog = cq_program()
    qbits = prog.allocate_qubits(2)

    # Rotation layer
    for i, w in enumerate(weights[:2]):
        prog << RY(qbits[0], w)
        prog << RZ(qbits[0], weights[2 + i])

    # Entangling layer
    prog << CNOT(qbits[0], qbits[1])

    # Second rotation
    for i, w in enumerate(weights[4:6]):
        prog << RY(qbits[1], w)
        prog << RZ(qbits[1], weights[6 + i])

    return prog

# Training loop would optimize weights
# using measured expectation values
```
""",
        }

        # Load bundled documents
        for doc_name, content in bundled_docs.items():
            documents.append(
                {
                    "id": doc_name,
                    "title": doc_name.replace("_", " ").title(),
                    "content": content,
                    "source": "bundled",
                }
            )

        # Try to load from filesystem if available
        if self.docs_dir.exists():
            for doc_file in self.docs_dir.glob("*.md"):
                try:
                    with open(doc_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        documents.append(
                            {
                                "id": doc_file.stem,
                                "title": doc_file.stem.replace("_", " ").title(),
                                "content": content,
                                "source": "filesystem",
                            }
                        )
                except Exception as e:
                    print(f"Warning: Could not read {doc_file}: {e}")

        return documents

    def index_documents(self, documents: list) -> bool:
        """Add documents to Qdrant collection"""
        if not self.client or not documents:
            return False

        print(f"Indexing {len(documents)} documents...")

        try:
            points = []
            for idx, doc in enumerate(documents):
                # Generate embedding
                text_content = f"{doc['title']} {doc['content']}"
                embedding = self._generate_simple_embedding(text_content)

                # Create point
                point = PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={
                        "id": doc["id"],
                        "title": doc["title"],
                        "content": doc["content"][: 2000],  # Limit payload size
                        "source": doc["source"],
                        "timestamp": int(time.time()),
                    },
                )
                points.append(point)

            # Upload points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            print(f"  ✓ Indexed {len(points)} documents successfully")
            return True

        except Exception as e:
            print(f"  Error indexing documents: {e}")
            return False

    def verify(self) -> bool:
        """Verify RAG initialization"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            point_count = collection_info.points_count
            print(f"✓ RAG initialized with {point_count} documents")
            return True
        except Exception as e:
            print(f"✗ RAG verification failed: {e}")
            return False

    def run(self) -> bool:
        """Run full initialization"""
        print("\n" + "=" * 50)
        print("CVGen RAG Initialization")
        print("=" * 50 + "\n")

        # Connect to Qdrant
        if not self.connect():
            print("Failed to connect to Qdrant")
            return False

        # Load documents
        documents = self._load_documents()
        print(f"Loaded {len(documents)} documents")

        # Index documents
        if not self.index_documents(documents):
            print("Warning: Document indexing failed")
            # Don't fail completely - RAG can be populated later
            return True

        # Verify
        if not self.verify():
            print("Warning: RAG verification failed")
            return True

        print("\n" + "=" * 50)
        print("RAG Initialization Complete!")
        print("=" * 50 + "\n")
        return True


if __name__ == "__main__":
    initializer = RAGInitializer()
    success = initializer.run()
    exit(0 if success else 1)
