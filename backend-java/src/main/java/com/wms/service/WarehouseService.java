package com.wms.service;

import com.wms.entity.Location;
import com.wms.entity.Warehouse;
import com.wms.repository.LocationRepository;
import com.wms.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class WarehouseService {

    private final WarehouseRepository warehouseRepository;
    private final LocationRepository locationRepository;

    public List<Warehouse> listAll() {
        return warehouseRepository.findAll();
    }

    public List<Location> getLocationsByWarehouse(Long warehouseId) {
        return locationRepository.findByWarehouseId(warehouseId);
    }
}
