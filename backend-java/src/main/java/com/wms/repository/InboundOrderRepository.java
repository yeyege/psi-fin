package com.wms.repository;

import com.wms.entity.InboundOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * 入库单 Repository — 候选人需要实现
 */
@Repository
public interface InboundOrderRepository extends JpaRepository<InboundOrder, Long> {

    // 用于生成入库单号时查询当天最大序号
    // 提示：可以写一个 @Query 查询当天创建的订单数
}
