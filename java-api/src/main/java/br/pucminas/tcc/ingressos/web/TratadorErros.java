package br.pucminas.tcc.ingressos.web;

import br.pucminas.tcc.ingressos.domain.RegraNegocioException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

/** Converte códigos de regra de negócio em HTTP 404 (não encontrado) ou 422 (demais). */
@RestControllerAdvice
public class TratadorErros {

    @ExceptionHandler(RegraNegocioException.class)
    public ResponseEntity<Map<String, String>> regraNegocio(RegraNegocioException e) {
        boolean naoEncontrado = e.getCodigo().endsWith("_NAO_ENCONTRADO") || e.getCodigo().endsWith("_NAO_ENCONTRADA");
        HttpStatus status = naoEncontrado ? HttpStatus.NOT_FOUND : HttpStatus.UNPROCESSABLE_ENTITY;
        return ResponseEntity.status(status).body(Map.of("erro", e.getCodigo()));
    }
}
