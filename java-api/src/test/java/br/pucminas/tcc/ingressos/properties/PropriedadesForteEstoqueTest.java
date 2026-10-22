package br.pucminas.tcc.ingressos.properties;

import br.pucminas.tcc.ingressos.properties.ApoioForte.OperacaoEstoque;
import br.pucminas.tcc.ingressos.properties.Geradores.Cenario;
import br.pucminas.tcc.ingressos.properties.Geradores.ItemSpec;
import br.pucminas.tcc.ingressos.properties.Geradores.Montado;
import net.jqwik.api.Arbitrary;
import net.jqwik.api.ForAll;
import net.jqwik.api.Property;
import net.jqwik.api.Provide;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

import static br.pucminas.tcc.ingressos.properties.ApoioForte.codigoDoErro;
import static br.pucminas.tcc.ingressos.properties.Geradores.verificar;

/**
 * Suíte forte, P17 (Disponibilidade e Status): modelo de referência do estoque e dos status
 * sob uma sequência de operações sobre várias reservas (R15–R19).
 */
class PropriedadesForteEstoqueTest {

    @Provide
    Arbitrary<Cenario> cenario() {
        return Geradores.cenarios();
    }

    @Provide
    Arbitrary<List<List<ItemSpec>>> outrasReservas() {
        return Geradores.itens().list().ofMinSize(1).ofMaxSize(5).list().ofMinSize(1).ofMaxSize(3);
    }

    @Provide
    Arbitrary<List<OperacaoEstoque>> operacoes() {
        return ApoioForte.operacoesEstoque().list().ofMinSize(1).ofMaxSize(12);
    }

    /** P17 – estoque e status coincidem com o modelo após cada operação. */
    @Property
    void p17ModeloDeEstoque(@ForAll("cenario") Cenario c, @ForAll("outrasReservas") List<List<ItemSpec>> outras,
                            @ForAll("operacoes") List<OperacaoEstoque> operacoes) {
        Montado m = new Montado(c.lotes());
        List<List<ItemSpec>> pedidos = new ArrayList<>();
        pedidos.add(c.itens());
        pedidos.addAll(outras);
        List<String> reservas = new ArrayList<>();
        for (List<ItemSpec> lista : pedidos) {
            reservas.add(m.reservar(lista).getId());
        }
        // modelo
        int[] disponivel = c.lotes().stream().mapToInt(l -> l.total()).toArray();
        String[] status = new String[reservas.size()];
        Arrays.fill(status, "CRIADA");
        List<int[]> demanda = new ArrayList<>();
        for (List<ItemSpec> lista : pedidos) {
            demanda.add(m.pedidoPorLote(lista));
        }

        for (OperacaoEstoque o : operacoes) {
            int k = o.reserva() % reservas.size();
            String op = o.op();
            String esperadoErro = null;
            String novoStatus = ApoioForte.destino(status[k], op);
            if (novoStatus == null) {
                esperadoErro = "TRANSICAO_INVALIDA";
            } else if (op.equals("CONFIRMAR") && excede(demanda.get(k), disponivel)) {
                esperadoErro = "DISPONIBILIDADE_INSUFICIENTE";
                novoStatus = null;
            }
            String id = reservas.get(k);
            String erro = codigoDoErro(() -> {
                switch (op) {
                    case "CONFIRMAR": m.servico.confirmar(id); break;
                    case "CANCELAR": m.servico.cancelar(id); break;
                    case "EXPIRAR": m.servico.expirar(id); break;
                    case "PAGAR": m.servico.pagar(id); break;
                    default: throw new IllegalStateException(op);
                }
            });
            verificar(Objects.equals(erro, esperadoErro),
                    op + " na reserva " + k + " (" + status[k] + "): esperado " + esperadoErro + ", obtido " + erro);
            if (novoStatus != null) {
                int[] d = demanda.get(k);
                if (op.equals("CONFIRMAR")) {
                    for (int i = 0; i < d.length; i++) {
                        disponivel[i] -= d[i];
                    }
                } else if ((op.equals("CANCELAR") || op.equals("EXPIRAR")) && status[k].equals("CONFIRMADA")) {
                    for (int i = 0; i < d.length; i++) {
                        disponivel[i] += d[i];
                    }
                }
                status[k] = novoStatus;
            }
            int[] real = m.disponibilidades();
            verificar(Arrays.equals(real, disponivel),
                    "estoque " + Arrays.toString(real) + " != modelo " + Arrays.toString(disponivel) + " após " + op);
            for (int j = 0; j < reservas.size(); j++) {
                String s = m.servico.buscarReserva(reservas.get(j)).getStatus().name();
                verificar(s.equals(status[j]), "reserva " + j + ": status " + s + " != modelo " + status[j]);
            }
        }
    }

    private static boolean excede(int[] pedido, int[] disponivel) {
        for (int i = 0; i < pedido.length; i++) {
            if (pedido[i] > disponivel[i]) {
                return true;
            }
        }
        return false;
    }
}
