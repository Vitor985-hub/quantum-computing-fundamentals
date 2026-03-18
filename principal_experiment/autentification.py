from qiskit_ibm_runtime import QiskitRuntimeService

# insira seu token aqui
QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform", 
    token='', 
    overwrite=True
)

print("✅ Conta configurada com sucesso!")