package br.pucminas.tcc.ingressos.examples;

import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.Totais;
import br.pucminas.tcc.ingressos.domain.Cupom;
import br.pucminas.tcc.ingressos.domain.Evento;
import br.pucminas.tcc.ingressos.domain.Lote;
import br.pucminas.tcc.ingressos.domain.Modelos.StatusEvento;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;
import br.pucminas.tcc.ingressos.domain.RegraNegocioException;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import net.jqwik.api.Example;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Executa os casos de exemplo compartilhados (shared/casos-exemplo.json).
 * Os mesmos casos rodam na implementação Node.js: é a evidência de equivalência funcional.
 */
class CasosExemploTest {

    @Example
    @SuppressWarnings("unchecked")
    void casosCompartilhados() throws IOException {
        List<Object> casos = (List<Object>) Json.ler(Files.readString(localizarCasos(), StandardCharsets.UTF_8));
        List<String> falhas = new ArrayList<>();
        for (Object c : casos) {
            Map<String, Object> caso = (Map<String, Object>) c;
            try {
                executar(caso);
            } catch (AssertionError e) {
                falhas.add(caso.get("nome") + ": " + e.getMessage());
            }
        }
        if (!falhas.isEmpty()) {
            throw new AssertionError(String.join("\n", falhas));
        }
    }

    private static Path localizarCasos() {
        Path dir = Path.of("").toAbsolutePath();
        while (dir != null) {
            Path candidato = dir.resolve("shared").resolve("casos-exemplo.json");
            if (Files.exists(candidato)) {
                return candidato;
            }
            dir = dir.getParent();
        }
        throw new IllegalStateException("shared/casos-exemplo.json não encontrado");
    }

    @SuppressWarnings("unchecked")
    private static void executar(Map<String, Object> caso) {
        ServicoIngressos servico = new ServicoIngressos();
        Map<String, String> salvos = new HashMap<>();
        List<Object> passos = (List<Object>) caso.get("passos");
        for (int i = 0; i < passos.size(); i++) {
            Map<String, Object> passo = (Map<String, Object>) passos.get(i);
            String op = (String) passo.get("op");
            List<Object> args = new ArrayList<>();
            for (Object a : (List<Object>) passo.get("args")) {
                args.add(a instanceof String && ((String) a).startsWith("$") ? salvos.get(((String) a).substring(1)) : a);
            }
            String contexto = "passo " + i + " (" + op + ")";
            Map<String, Object> resultado = null;
            String erro = null;
            try {
                resultado = invocar(servico, op, args);
            } catch (RegraNegocioException e) {
                erro = e.getCodigo();
            }
            if (passo.containsKey("erro")) {
                if (!Objects.equals(erro, passo.get("erro"))) {
                    throw new AssertionError(contexto + ": esperado erro " + passo.get("erro") + ", obtido " + erro);
                }
                continue;
            }
            if (erro != null) {
                throw new AssertionError(contexto + ": erro inesperado " + erro);
            }
            if (passo.containsKey("salvar")) {
                salvos.put((String) passo.get("salvar"), (String) resultado.get("id"));
            }
            Map<String, Object> espera = (Map<String, Object>) passo.getOrDefault("espera", Map.of());
            for (Map.Entry<String, Object> e : espera.entrySet()) {
                Object obtido = resultado.get(e.getKey());
                if (!Objects.equals(String.valueOf(obtido), String.valueOf(e.getValue()))) {
                    throw new AssertionError(contexto + ": campo " + e.getKey() + " esperado " + e.getValue() + ", obtido " + obtido);
                }
            }
        }
    }

    private static int inteiro(Object o) { return ((Long) o).intValue(); }
    private static long longo(Object o) { return (Long) o; }
    private static String texto(Object o) { return (String) o; }

    /** Despacha a operação do caso para o serviço e devolve o resultado como mapa de campos. */
    private static Map<String, Object> invocar(ServicoIngressos s, String op, List<Object> a) {
        switch (op) {
            case "criarEvento": return evento(s.criarEvento(texto(a.get(0)), texto(a.get(1)), texto(a.get(2)), inteiro(a.get(3))));
            case "alterarStatusEvento": return evento(s.alterarStatusEvento(texto(a.get(0)), StatusEvento.valueOf(texto(a.get(1)))));
            case "criarLote": return lote(s.criarLote(texto(a.get(0)), texto(a.get(1)), longo(a.get(2)), inteiro(a.get(3))));
            case "buscarLote": return lote(s.buscarLote(texto(a.get(0))));
            case "cadastrarCupom": return cupom(s.cadastrarCupom(texto(a.get(0)), TipoCupom.valueOf(texto(a.get(1))), longo(a.get(2)),
                    longo(a.get(3)), (Long) a.get(4), texto(a.get(5))));
            case "criarReserva": return reserva(s.criarReserva(texto(a.get(0))));
            case "buscarReserva": return reserva(s.buscarReserva(texto(a.get(0))));
            case "adicionarItem": return reserva(s.adicionarItem(texto(a.get(0)), texto(a.get(1)), inteiro(a.get(2))));
            case "aplicarCupom": return reserva(s.aplicarCupom(texto(a.get(0)), texto(a.get(1))));
            case "confirmar": return reserva(s.confirmar(texto(a.get(0))));
            case "pagar": return reserva(s.pagar(texto(a.get(0))));
            case "cancelar": return reserva(s.cancelar(texto(a.get(0))));
            case "expirar": return reserva(s.expirar(texto(a.get(0))));
            case "calcularTotais": return totais(s.calcularTotais(texto(a.get(0)), texto(a.get(1))));
            default: throw new IllegalArgumentException("operação desconhecida: " + op);
        }
    }

    private static Map<String, Object> evento(Evento e) {
        return Map.of("id", e.getId(), "status", e.getStatus().name(), "capacidade", e.getCapacidade());
    }

    private static Map<String, Object> lote(Lote l) {
        return Map.of("id", l.getId(), "quantidadeTotal", l.getQuantidadeTotal(),
                "quantidadeDisponivel", l.getQuantidadeDisponivel(), "precoCentavos", l.getPrecoCentavos());
    }

    private static Map<String, Object> cupom(Cupom c) {
        return Map.of("id", c.getCodigo(), "valor", c.getValor());
    }

    private static Map<String, Object> reserva(Reserva r) {
        return Map.of("id", r.getId(), "status", r.getStatus().name());
    }

    private static Map<String, Object> totais(Totais t) {
        return Map.of("subtotal", t.getSubtotal(), "desconto", t.getDesconto(), "total", t.getTotal());
    }
}
