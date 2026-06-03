package com.insuramind.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

@Component
public class AiServiceClient {
    private final WebClient webClient;

    public AiServiceClient(@Value("${app.ai.base-url}") String baseUrl) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
    }

    public void process(ProcessDocumentRequest request) {
        webClient.post()
                .uri("/process")
                .bodyValue(request)
                .retrieve()
                .toBodilessEntity()
                .block();
    }

    public AiQueryResponse query(AiQueryRequest request) {
        return webClient.post()
                .uri("/query")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(AiQueryResponse.class)
                .block();
    }
}
