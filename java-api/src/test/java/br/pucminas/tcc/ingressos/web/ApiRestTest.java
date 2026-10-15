package br.pucminas.tcc.ingressos.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Teste de fumaça da camada REST (fora da medição de mutação). Requer Maven: mvn test. */
@SpringBootTest
@AutoConfigureMockMvc
class ApiRestTest {

    @Autowired
    MockMvc mvc;

    @Test
    void criaEventoEConsulta() throws Exception {
        mvc.perform(post("/eventos").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"nome\":\"Show\",\"data\":\"2026-12-01\",\"local\":\"BH\",\"capacidade\":100}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("ATIVO"));
    }

    @Test
    void reservaInexistenteDevolve404() throws Exception {
        mvc.perform(get("/reservas/RES-999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.erro").value("RESERVA_NAO_ENCONTRADA"));
    }

    @Test
    void eventoInvalidoDevolve422() throws Exception {
        mvc.perform(post("/eventos").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"nome\":\"Show\",\"data\":\"2026-12-01\",\"local\":\"BH\",\"capacidade\":0}"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.erro").value("DADOS_INVALIDOS"));
    }
}
