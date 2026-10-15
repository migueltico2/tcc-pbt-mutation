package br.pucminas.tcc.ingressos.web;

import br.pucminas.tcc.ingressos.domain.ServicoIngressos;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

/** Aplicação Spring Boot. O domínio é Java puro e entra como um único bean (decisão D1). */
@SpringBootApplication
public class IngressosApplication {

    public static void main(String[] args) {
        SpringApplication.run(IngressosApplication.class, args);
    }

    @Bean
    ServicoIngressos servicoIngressos() {
        return new ServicoIngressos();
    }

    @Bean
    Clock relogio() {
        return Clock.systemDefaultZone();
    }
}
