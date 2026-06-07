package com.insuramind.chat.dto;

public record CitationDto(
        String citationLabel,
        Integer pageNumber,
        String sectionType,
        String heading,
        String text,
        double score
) {}
