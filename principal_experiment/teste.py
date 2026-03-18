from qiskit_ibm_runtime import QiskitRuntimeService

# Forçamos o canal que você acabou de configurar
try:
    service = QiskitRuntimeService(channel="ibm_quantum_platform")
    print("✅ Conexão bem-sucedida!")
    
    # Listar os backends disponíveis para confirmar
    backends = service.backends()
    print(f"Backends encontrados: {[b.name for b in backends]}")
except Exception as e:
    print(f"❌ Erro ao carregar o serviço: {e}")