package com.wms.controller;

import com.wms.common.ApiResponse;
import com.wms.dto.InboundOrderCreateRequest;
import com.wms.dto.InventoryResponse;
import com.wms.service.InventoryService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * ============================================
 *  候选人需要实现以下接口：
 * ============================================
 *
 * POST /api/inbound-orders         — 创建入库单（任务1）
 * GET  /api/inventory              — 库存查询（任务2）
 *
 * 候选人在 InventoryService 中实现业务逻辑后，
 * 在此 Controller 中补全对应的接口方法。
 */
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class InventoryController {

    private final InventoryService inventoryService;

    /**
     * 创建入库单 — 候选人实现
     */
    @PostMapping("/inbound-orders")
    public ApiResponse<?> createInboundOrder(@Valid @RequestBody InboundOrderCreateRequest request) {
        // TODO: 调用 inventoryService.createInboundOrder(request)
        return ApiResponse.error(501, "请实现入库单创建功能（任务1）");
    }

    /**
     * 库存查询 — 候选人实现
     */
    @GetMapping("/inventory")
    public ApiResponse<List<InventoryResponse>> queryInventory(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Long warehouseId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize) {
        // TODO: 调用 inventoryService.queryInventory(...)
        return ApiResponse.error(501, "请实现库存查询功能（任务2）");
    }
}
