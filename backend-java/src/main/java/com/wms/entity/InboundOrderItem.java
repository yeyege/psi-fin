package com.wms.entity;

import jakarta.persistence.*;
import lombok.*;

/**
 * 入库单明细 — 候选人需要实现
 */
@Entity
@Table(name = "inbound_order_items")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InboundOrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(nullable = false)
    private Integer quantity;

    @Column(name = "location_code", nullable = false, length = 50)
    private String locationCode;
}
