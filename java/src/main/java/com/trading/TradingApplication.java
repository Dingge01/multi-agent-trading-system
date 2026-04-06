package com.trading;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 多Agent量化交易系统 - Spring Boot 启动类
 *
 * 运行方式: mvn spring-boot:run
 * 或: java -jar target/multi-agent-trading-1.0.0.jar
 */
@SpringBootApplication
public class TradingApplication {
    public static void main(String[] args) {
        SpringApplication.run(TradingApplication.class, args);
    }
}
