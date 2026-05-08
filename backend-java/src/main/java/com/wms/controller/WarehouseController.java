package com.wms.controller;

import com.wms.common.ApiResponse;
import com.wms.entity.Location;
import com.wms.entity.Warehouse;
import com.wms.service.WarehouseService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class WarehouseController {

    private final WarehouseService warehouseService;

    @GetMapping("/warehouses")
    public ApiResponse<List<Warehouse>> listWarehouses() {
        return ApiResponse.success(warehouseService.listAll());
    }

    @GetMapping("/warehouses/{id}/locations")
    public ApiResponse<List<Location>> getLocations(@PathVariable Long id) {
        return ApiResponse.success(warehouseService.getLocationsByWarehouse(id));
    }
}
