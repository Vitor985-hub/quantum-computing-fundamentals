from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from collections import Counter
import pprint

def main():
    # Conexão e seleção de backend
    service = QiskitRuntimeService()
    all_backends = service.backends(operational=True)
    hardware_backends = [b for b in all_backends if not b.configuration().simulator]
    if not hardware_backends:
        raise SystemExit("Nenhum backend de hardware operacional encontrado.")
    backend = hardware_backends[0]
    print("Rodando no hardware:", backend.name)

    # Circuito simples: H + medida
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    qc.measure(0, 0)

    # Adaptar ao ISA do backend (preset pass manager) e transpile
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(qc)
    qc_optimized = transpile(isa_circuit, backend)

    shots = 1024

    # Instanciar Sampler diretamente com o backend (plano gratuito)
    sampler = Sampler(mode=backend)

    # Submeter job: circuitos como argumento posicional conforme assinatura
    job = sampler.run([qc_optimized], shots=shots)
    print("Job ID:", job.job_id())
    print("Aguardando resultado... (pode demorar dependendo da fila)")

    # Obter resultado (bloqueante) e inspecionar
    result = job.result()
    print("\n--- Inspeção do result ---")
    pprint.pprint(result)
    print("--- Fim da inspeção ---\n")

    # Extrair o primeiro SamplerPubResult
    pub_res = result[0]
    data = getattr(pub_res, "data", None)
    if data is None:
        raise RuntimeError("Resultado não contém atributo 'data'. Veja pprint(result).")

    bit_container = getattr(data, "c", None) or getattr(data, "bits", None) or getattr(data, "values", None)
    if bit_container is None:
        raise RuntimeError("Não encontrei BitArray em data.c nem campos alternativos. Veja pprint(result).")

    # Debug inicial
    print("DEBUG: bit_container type:", type(bit_container))
    print("DEBUG: sample attrs:", [a for a in dir(bit_container) if not a.startswith("_")][:60])
    num_shots = int(getattr(bit_container, "num_shots", 0))
    num_bits = int(getattr(bit_container, "num_bits", 1))
    print(f"BitArray detectado: num_shots={num_shots}, num_bits={num_bits}")

    bitstrings = None

    # 1) Preferencial: to01()
    if hasattr(bit_container, "to01"):
        try:
            s = bit_container.to01()
            expected = num_shots * num_bits
            if len(s) < expected:
                print(f"AVISO: to01() retornou comprimento {len(s)} < esperado {expected}.")
            if num_bits == 1:
                bitstrings = list(s)
            else:
                bitstrings = [s[i * num_bits:(i + 1) * num_bits].ljust(num_bits, "0") for i in range(num_shots)]
        except Exception as e:
            print("DEBUG: to01() falhou:", repr(e))

    # 2) tolist()
    if bitstrings is None and hasattr(bit_container, "tolist"):
        try:
            shots_list = bit_container.tolist()
            if shots_list and isinstance(shots_list[0], (list, tuple)):
                bitstrings = [''.join(str(int(b)) for b in shot) for shot in shots_list]
            else:
                bitstrings = [str(int(b)) for b in shots_list]
        except Exception as e:
            print("DEBUG: tolist() falhou:", repr(e))

    # 3) to_numpy()
    if bitstrings is None and hasattr(bit_container, "to_numpy"):
        try:
            arr = bit_container.to_numpy()
            if getattr(arr, "ndim", 1) == 2:
                bitstrings = [''.join(str(int(b)) for b in row) for row in arr]
            else:
                bitstrings = [str(int(x)) for x in arr]
        except Exception as e:
            print("DEBUG: to_numpy() falhou:", repr(e))

    # 4) tentar atributos internos comuns (_array, _bits, buffer)
    if bitstrings is None:
        tried_internal = False
        for attr in ("_array", "_bits", "buffer", "bits"):
            internal = getattr(bit_container, attr, None)
            if internal is None:
                continue
            tried_internal = True
            try:
                # se for numpy-like
                if hasattr(internal, "tolist"):
                    arr = internal.tolist()
                    if isinstance(arr, list) and arr and isinstance(arr[0], (list, tuple)):
                        bitstrings = [''.join(str(int(b)) for b in shot) for shot in arr]
                    else:
                        bitstrings = [str(int(x)) for x in arr]
                    break
                # se for bytes/bytearray, converter para bits
                if isinstance(internal, (bytes, bytearray, memoryview)):
                    bits = ''.join(f"{byte:08b}" for byte in internal)
                    if num_bits == 1:
                        bitstrings = list(bits[:num_shots])
                    else:
                        bitstrings = [bits[i * num_bits:(i + 1) * num_bits] for i in range(num_shots)]
                    break
            except Exception as e:
                print(f"DEBUG: leitura de atributo interno {attr} falhou:", repr(e))
    if tried_internal:
        print("DEBUG: tentou atributos internos.")

    # 5) slice_bits(i) com conversão segura do shot_bits
    if bitstrings is None and hasattr(bit_container, "slice_bits"):
        bitstrings = []
        for i in range(num_shots):
            try:
                shot_bits = bit_container.slice_bits(i)  # sua implementação aceita 1 arg
            except Exception as e:
                print(f"DEBUG: slice_bits({i}) falhou:", repr(e))
                raise RuntimeError("slice_bits falhou; verifique debug acima.") from e

            # converter shot_bits por métodos públicos
            bs = None
            if hasattr(shot_bits, "to01"):
                try:
                    bs = shot_bits.to01()
                except Exception as e:
                    print("DEBUG: shot_bits.to01() falhou:", repr(e))
            if bs is None and hasattr(shot_bits, "tolist"):
                try:
                    lst = shot_bits.tolist()
                    if isinstance(lst, (list, tuple)):
                        bs = ''.join(str(int(b)) for b in lst)
                    else:
                        bs = str(int(lst))
                except Exception as e:
                    print("DEBUG: shot_bits.tolist() falhou:", repr(e))
            if bs is None and hasattr(shot_bits, "to_numpy"):
                try:
                    arr = shot_bits.to_numpy()
                    if getattr(arr, "ndim", 1) == 1:
                        bs = ''.join(str(int(b)) for b in arr)
                    else:
                        bs = ''.join(str(int(b)) for b in arr.flatten())
                except Exception as e:
                    print("DEBUG: shot_bits.to_numpy() falhou:", repr(e))

            # 6) último recurso: tentar extrair via repr() com regex
            if bs is None:
                r = repr(shot_bits)
                print("DEBUG: shot_bits repr:", r[:400])
                # tenta extrair sequências de 0/1 do repr
                m = re.search(r"[01]{1,}", r)
                if m:
                    candidate = m.group(0)
                    if len(candidate) >= 1:
                        bs = candidate[-num_bits:] if num_bits > 0 else candidate
                else:
                    # tentar encontrar listas no repr: [0, 1, ...]
                    m2 = re.search(r"\[([01,\s]+)\]", r)
                    if m2:
                        nums = re.findall(r"[01]", m2.group(1))
                        bs = ''.join(nums)

            if bs is None:
                print("DEBUG: não foi possível converter shot_bits; repr e attrs acima foram impressos.")
                raise RuntimeError("Não foi possível converter shot_bits; verifique métodos disponíveis.")
            bitstrings.append(bs)

    # Se ainda nada, falhar com debug
    if bitstrings is None:
        print("DEBUG: Falha completa. Exibindo repr do bit_container (trecho):")
        try:
            print(repr(bit_container)[:1000])
        except Exception:
            pass
        raise RuntimeError("Não foi possível converter BitArray em bitstrings automaticamente. Veja debug acima.")

    # Contar e exibir
    counts = Counter(bitstrings)
    print("Contagens (raw):", dict(counts))
    total = sum(counts.values())
    for state, cnt in sorted(counts.items(), key=lambda x: x[0]):
        prob = (cnt / total) * 100 if total else 0.0
        print(f"Estado {state}: {cnt} shots -> {prob:.2f}%")

if __name__ == '__main__':
    main()