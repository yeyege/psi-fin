package com.wms.service;

import com.wms.dto.InboundOrderCreateRequest;
import com.wms.dto.InventoryResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * ============================================
 *  候选人需要实现以下两个方法：
 * ============================================
 *
 * 1. createInboundOrder() — 入库单创建（任务1）
 *    要求：
 *    - 生成入库单号（格式 IN-YYYYMMDD-XXX）
 *    - 校验商品和库位是否存在
 *    - 在事务中同时创建入库单和更新库存
 *    - 参数校验已在 DTO 层通过 @Valid 处理
 *
 * 2. queryInventory() — 库存查询（任务2）
 *    要求：
 *    - 支持按商品名称/SKU模糊搜索
 *    - 支持按仓库筛选
 *    - 支持分页
 *    - 返回关联的商品名称和仓库名称
 *    - 注意性能：使用 JOIN 查询而非 N+1
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InventoryService {

    // === 候选人需注入以下 Repository ===
    // private final InventoryRepository inventoryRepository;
    // private final InboundOrderRepository inboundOrderRepository;
    // private final InboundOrderItemRepository inboundOrderItemRepository;
    // private final ProductRepository productRepository;
    // private final LocationRepository locationRepository;

    /**
     * 入库单创建 — 候选人实现
     */
    // @Transactional
    public Object createInboundOrder(InboundOrderCreateRequest request) {
        // TODO: 候选人实现
        throw new UnsupportedOperationException("请实现入库单创建功能（任务1）");
    }

    /**
     * 库存查询 — 候选人实现
     */
    public List<InventoryResponse> queryInventory(String keyword, Long warehouseId,
                                                   int page, int pageSize) {
        // TODO: 候选人实现
        throw new UnsupportedOperationException("请实现库存查询功能（任务2）");
    }
}
