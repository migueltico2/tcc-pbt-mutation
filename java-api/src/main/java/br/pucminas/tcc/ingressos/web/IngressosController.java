package br.pucminas.tcc.ingressos.web;

import br.pucminas.tcc.ingressos.domain.CalculadoraPreco.Totais;
import br.pucminas.tcc.ingressos.domain.Cupom;
import br.pucminas.tcc.ingressos.domain.Evento;
import br.pucminas.tcc.ingressos.domain.Lote;
import br.pucminas.tcc.ingressos.domain.Modelos.StatusEvento;
import br.pucminas.tcc.ingressos.domain.Modelos.TipoCupom;
import br.pucminas.tcc.ingressos.domain.Reserva;
import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.LocalDate;
import java.util.List;

/**
 * Camada REST fina (decisão D2): converte JSON em chamadas ao domínio. Não contém regra de negócio
 * e fica fora da análise de mutação. Mesmas rotas da node-api (src/web/app.js).
 */
@RestController
public class IngressosController {

    record NovoEvento(String nome, String data, String local, int capacidade) { }
    record NovoStatusEvento(StatusEvento status) { }
    record NovoLote(String nome, long precoCentavos, int quantidadeTotal) { }
    record NovoCupom(String codigo, TipoCupom tipo, long valor, Long minimoCentavos, Long maximoDescontoCentavos, String validoAte) { }
    record NovaReserva(String eventoId) { }
    record NovoItem(String loteId, int quantidade) { }
    record CodigoCupom(String codigo) { }
    record ReservaComTotais(String id, String eventoId, List<Reserva.Item> itens, String codigoCupom, String status, Totais totais) { }

    private final ServicoIngressos servico;
    private final Clock relogio;

    public IngressosController(ServicoIngressos servico, Clock relogio) {
        this.servico = servico;
        this.relogio = relogio;
    }

    private ReservaComTotais comTotais(Reserva r) {
        Totais totais = servico.calcularTotais(r.getId(), LocalDate.now(relogio).toString());
        return new ReservaComTotais(r.getId(), r.getEventoId(), r.getItens(), r.getCodigoCupom(), r.getStatus().name(), totais);
    }

    @PostMapping("/eventos")
    @ResponseStatus(HttpStatus.CREATED)
    public Evento criarEvento(@RequestBody NovoEvento e) {
        return servico.criarEvento(e.nome(), e.data(), e.local(), e.capacidade());
    }

    @GetMapping("/eventos/{id}")
    public Evento buscarEvento(@PathVariable String id) {
        return servico.buscarEvento(id);
    }

    @PatchMapping("/eventos/{id}/status")
    public Evento alterarStatusEvento(@PathVariable String id, @RequestBody NovoStatusEvento s) {
        return servico.alterarStatusEvento(id, s.status());
    }

    @PostMapping("/eventos/{id}/lotes")
    @ResponseStatus(HttpStatus.CREATED)
    public Lote criarLote(@PathVariable String id, @RequestBody NovoLote l) {
        return servico.criarLote(id, l.nome(), l.precoCentavos(), l.quantidadeTotal());
    }

    @GetMapping("/lotes/{id}")
    public Lote buscarLote(@PathVariable String id) {
        return servico.buscarLote(id);
    }

    @PostMapping("/cupons")
    @ResponseStatus(HttpStatus.CREATED)
    public Cupom cadastrarCupom(@RequestBody NovoCupom c) {
        long minimo = c.minimoCentavos() == null ? 0 : c.minimoCentavos();
        return servico.cadastrarCupom(c.codigo(), c.tipo(), c.valor(), minimo, c.maximoDescontoCentavos(), c.validoAte());
    }

    @PostMapping("/reservas")
    @ResponseStatus(HttpStatus.CREATED)
    public ReservaComTotais criarReserva(@RequestBody NovaReserva r) {
        return comTotais(servico.criarReserva(r.eventoId()));
    }

    @GetMapping("/reservas/{id}")
    public ReservaComTotais buscarReserva(@PathVariable String id) {
        return comTotais(servico.buscarReserva(id));
    }

    @PostMapping("/reservas/{id}/itens")
    public ReservaComTotais adicionarItem(@PathVariable String id, @RequestBody NovoItem i) {
        return comTotais(servico.adicionarItem(id, i.loteId(), i.quantidade()));
    }

    @PutMapping("/reservas/{id}/cupom")
    public ReservaComTotais aplicarCupom(@PathVariable String id, @RequestBody CodigoCupom c) {
        return comTotais(servico.aplicarCupom(id, c.codigo()));
    }

    @PostMapping("/reservas/{id}/confirmacao")
    public ReservaComTotais confirmar(@PathVariable String id) {
        return comTotais(servico.confirmar(id));
    }

    @PostMapping("/reservas/{id}/pagamento")
    public ReservaComTotais pagar(@PathVariable String id) {
        return comTotais(servico.pagar(id));
    }

    @PostMapping("/reservas/{id}/cancelamento")
    public ReservaComTotais cancelar(@PathVariable String id) {
        return comTotais(servico.cancelar(id));
    }

    @PostMapping("/reservas/{id}/expiracao")
    public ReservaComTotais expirar(@PathVariable String id) {
        return comTotais(servico.expirar(id));
    }
}
