package com.insuramind;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync
@SpringBootApplication
public class InsuraMindApplication {
    public static void main(String[] args) {
        SpringApplication.run(InsuraMindApplication.class, args);
    }
}
