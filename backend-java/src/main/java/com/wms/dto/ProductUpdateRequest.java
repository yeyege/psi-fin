package com.wms.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ProductUpdateRequest {
    @NotBlank(message = "商品名称不能为空")
    @Size(max = 200)
    private String name;

    @Size(max = 20)
    private String unit;
}
