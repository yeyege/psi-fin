package com.wms.repository;

import com.wms.entity.Inventory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * 库存 Repository — 候选人需要实现库存查询（任务2）
 * 提示：你可能需要添加自定义查询方法
 */
@Repository
public interface InventoryRepository extends JpaRepository<Inventory, Long> {

    Optional<Inventory> findByProductIdAndLocationCode(Long productId, String locationCode);

    // TODO: 候选人添加自定义查询方法，支持按 product/sku/location 筛选和分页
    // 提示：可以使用 @Query 写 JPQL，或使用 Specification 动态查询
}
