package com.wms.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 库存查询响应 — 候选人需要实现库存查询接口
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class InventoryResponse {
    private Long productId;
    private String productName;
    private String sku;
    private String locationCode;
    private String warehouseName;
    private Integer quantity;
    private LocalDateTime updatedAt;
}
