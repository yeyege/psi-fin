package com.wms.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * 入库单创建请求 — 候选人需要实现对应的 Controller 和 Service
 */
@Data
public class InboundOrderCreateRequest {

    @NotBlank(message = "供应商名称不能为空")
    private String supplierName;

    @NotEmpty(message = "入库明细不能为空")
    @Valid
    private List<InboundItemRequest> items;
}

@Data
class InboundItemRequest {
    @NotNull(message = "商品ID不能为空")
    private Long productId;

    @Min(value = 1, message = "数量必须大于0")
    private Integer quantity;

    @NotBlank(message = "库位编码不能为空")
    private String locationCode;
}
