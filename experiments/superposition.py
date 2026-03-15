from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

# 1. Cria o circuito (1 Qubit, 1 Bit Clássico)
# Dica: passar os números inteiros em vez de lista [0] na medição é mais limpo.
qc = QuantumCircuit(1, 1)

# 2. Cria a superposição
qc.h(0)

# 3. Mede o qubit 0 e guarda no bit clássico 0
qc.measure(0, 0)

# 4. Inicializa o simulador
simulator = AerSimulator()

# 5. Transpila o circuito para o simulador (Melhor prática atual do Qiskit)
compiled_circuit = transpile(qc, simulator)

# 6. Executa o circuito transpilado
result = simulator.run(compiled_circuit, shots=1000).result()
counts = result.get_counts(compiled_circuit)

print("Resultados da medição:", counts)

# 7. Plota o histograma de forma segura para qualquer IDE
fig = plot_histogram(counts)
plt.show() # Exibe a janela com o gráfico