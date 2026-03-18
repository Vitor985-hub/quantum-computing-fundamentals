from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

service = QiskitRuntimeService(channel="ibm_quantum_platform")

backend = service.least_busy(simulator=False, operational=True)
print(f'rodando no hardware: {backend.name}')

qc = QuantumCircuit(1, 1)
qc.h(0)
qc.measure(0, 0)

qc_optimized = transpile(qc, backend)

Sampler = Sampler(mode=backend)
job = Sampler.run([qc_optimized], shots=1024)

print(f'job ID: {job.job_id()}')
print('Aguardando resultado... (isso pode levar alguns minutos)')

result = job.result()
pub_result = result[0]
data = pub_result.data
nome_do_registro = list(data.keys())[0]
counts = data[nome_do_registro].get_counts()

print("\n" + "="*40)
print(f"RESULTADO REAL DO COLAPSO (Hardware: {backend.name})")
print(f"Registrado como: {nome_do_registro}")
print(f"Contagens: {counts}")
print("="*40)
 
total = sum(counts.values())
p0 = (counts.get('0', 0) / total) * 100
p1 = (counts.get('1', 0) / total) * 100

print(f"Probabilidade de |0>: {p0:.2f}%")
print(f"Probabilidade de |1>: {p1:.2f}%")