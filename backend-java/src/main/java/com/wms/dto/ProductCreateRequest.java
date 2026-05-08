package com.wms.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ProductCreateRequest {
    @NotBlank(message = "商品名称不能为空")
    @Size(max = 200, message = "商品名称最长200个字符")
    private String name;

    @NotBlank(message = "SKU不能为空")
    @Size(max = 50, message = "SKU最长50个字符")
    private String sku;

    private String unit = "个";
}
