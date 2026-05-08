package com.wms.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * 入库单主表 — 候选人需要实现创建功能
 */
@Entity
@Table(name = "inbound_orders")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InboundOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_no", nullable = false, unique = true, length = 50)
    private String orderNo;

    @Column(name = "supplier_name", length = 200)
    private String supplierName;

    @Column(length = 20)
    @Builder.Default
    private String status = "DRAFT";

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    // 候选人在实现时可按需处理明细关联
    // @OneToMany(mappedBy = "orderId", cascade = CascadeType.ALL, orphanRemoval = true)

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
