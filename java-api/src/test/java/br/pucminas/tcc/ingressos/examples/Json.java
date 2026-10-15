package br.pucminas.tcc.ingressos.examples;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Leitor JSON mínimo, suficiente para shared/casos-exemplo.json (objetos, listas, strings sem escapes
 * especiais, números inteiros, true/false/null). Evita dependências extras nos testes.
 */
final class Json {

    private final String texto;
    private int pos;

    private Json(String texto) {
        this.texto = texto;
    }

    static Object ler(String texto) {
        Json json = new Json(texto);
        Object valor = json.valor();
        json.espacos();
        if (json.pos != texto.length()) {
            throw new IllegalArgumentException("JSON com conteúdo sobrando na posição " + json.pos);
        }
        return valor;
    }

    private void espacos() {
        while (pos < texto.length() && Character.isWhitespace(texto.charAt(pos))) {
            pos++;
        }
    }

    private Object valor() {
        espacos();
        char c = texto.charAt(pos);
        if (c == '{') return objeto();
        if (c == '[') return lista();
        if (c == '"') return string();
        if (texto.startsWith("true", pos)) { pos += 4; return Boolean.TRUE; }
        if (texto.startsWith("false", pos)) { pos += 5; return Boolean.FALSE; }
        if (texto.startsWith("null", pos)) { pos += 4; return null; }
        return numero();
    }

    private Map<String, Object> objeto() {
        Map<String, Object> mapa = new LinkedHashMap<>();
        pos++;
        espacos();
        if (texto.charAt(pos) == '}') { pos++; return mapa; }
        while (true) {
            espacos();
            String chave = string();
            espacos();
            pos++; // ':'
            mapa.put(chave, valor());
            espacos();
            char c = texto.charAt(pos++);
            if (c == '}') return mapa;
        }
    }

    private List<Object> lista() {
        List<Object> itens = new ArrayList<>();
        pos++;
        espacos();
        if (texto.charAt(pos) == ']') { pos++; return itens; }
        while (true) {
            itens.add(valor());
            espacos();
            char c = texto.charAt(pos++);
            if (c == ']') return itens;
        }
    }

    private String string() {
        int inicio = ++pos;
        while (texto.charAt(pos) != '"') {
            pos++;
        }
        return texto.substring(inicio, pos++);
    }

    private Long numero() {
        int inicio = pos;
        if (texto.charAt(pos) == '-') pos++;
        while (pos < texto.length() && Character.isDigit(texto.charAt(pos))) pos++;
        return Long.parseLong(texto.substring(inicio, pos));
    }
}
