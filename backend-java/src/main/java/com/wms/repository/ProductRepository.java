package com.wms.repository;

import com.wms.entity.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {

    boolean existsBySku(String sku);

    /**
     * 模糊搜索商品（按名称或SKU）
     */
    @Query("SELECT p FROM Product p WHERE " +
           "(:keyword IS NULL OR p.name LIKE %:keyword% OR p.sku LIKE %:keyword%)")
    List<Product> search(@Param("keyword") String keyword);
}
