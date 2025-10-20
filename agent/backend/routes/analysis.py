#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flow analysis endpoints
"""

from fastapi import APIRouter, HTTPException
import pandas as pd
from models import (
    ProvinceFlowRequest, ProvinceFlowResponse, ProvinceFlowRecord,
    CityFlowRequest, CityFlowResponse, CityFlowRecord,
    ProvinceCorridorRequest, ProvinceCorridorResponse, CorridorRecord,
    CityCorridorRequest, CityCorridorResponse, CityCorridorRecord
)
from analysis import (
    analyze_province_flow,
    analyze_city_flow,
    analyze_province_corridor,
    analyze_city_corridor
)

router = APIRouter()


@router.post("/analyze/province-flow", response_model=ProvinceFlowResponse)
def analyze_province_flow_endpoint(request: ProvinceFlowRequest):
    """
    Analyze province-level flow intensity and ranking
    
    Supports:
    - Daily analysis and Spring Festival prediction
    - Time dimension: daily or total
    - Direction: send or arrive
    """
    try:
        df = analyze_province_flow(
            period_type=request.period_type,
            start=request.start,
            end=request.end,
            date_mode=request.date_mode.value,
            direction=request.direction.value,
            dyna_type=request.dyna_type
        )
        
        records = []
        for _, row in df.iterrows():
            records.append(ProvinceFlowRecord(
                province=str(row['province']),
                date=str(row['date']) if pd.notna(row.get('date')) else None,
                flow=float(row['flow']),
                rank=int(row['rank'])
            ))
        
        return ProvinceFlowResponse(
            period_type=request.period_type,
            date_mode=request.date_mode.value,
            direction=request.direction.value,
            total_records=len(records),
            data=records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/city-flow", response_model=CityFlowResponse)
def analyze_city_flow_endpoint(request: CityFlowRequest):
    """
    Analyze city-level flow intensity and ranking
    """
    try:
        df = analyze_city_flow(
            period_type=request.period_type,
            start=request.start,
            end=request.end,
            date_mode=request.date_mode.value,
            direction=request.direction.value,
            dyna_type=request.dyna_type
        )
        
        records = []
        for _, row in df.iterrows():
            records.append(CityFlowRecord(
                city=str(row['city']),
                date=str(row['date']) if pd.notna(row.get('date')) else None,
                flow=float(row['flow']),
                rank=int(row['rank'])
            ))
        
        return CityFlowResponse(
            period_type=request.period_type,
            date_mode=request.date_mode.value,
            direction=request.direction.value,
            total_records=len(records),
            data=records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/province-corridor", response_model=ProvinceCorridorResponse)
def analyze_province_corridor_endpoint(request: ProvinceCorridorRequest):
    """
    Analyze top inter-province corridors
    """
    try:
        df = analyze_province_corridor(
            period_type=request.period_type,
            start=request.start,
            end=request.end,
            date_mode=request.date_mode.value,
            topk=request.topk,
            dyna_type=request.dyna_type
        )
        
        records = []
        for _, row in df.iterrows():
            records.append(CorridorRecord(
                send_province=str(row['send_province']),
                arrive_province=str(row['arrive_province']),
                flow=float(row['flow']),
                rank=int(row['rank'])
            ))
        
        return ProvinceCorridorResponse(
            period_type=request.period_type,
            date_mode=request.date_mode.value,
            topk=request.topk,
            total_records=len(records),
            data=records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/city-corridor", response_model=CityCorridorResponse)
def analyze_city_corridor_endpoint(request: CityCorridorRequest):
    """
    Analyze top city corridors (intra-province and inter-province)
    """
    try:
        result = analyze_city_corridor(
            period_type=request.period_type,
            start=request.start,
            end=request.end,
            date_mode=request.date_mode.value,
            topk_intra=request.topk_intra,
            topk_inter=request.topk_inter,
            dyna_type=request.dyna_type
        )
        
        intra_records = []
        for _, row in result['intra_province'].iterrows():
            intra_records.append(CityCorridorRecord(
                send_city=str(row['send_city']),
                arrive_city=str(row['arrive_city']),
                flow=float(row['flow']),
                rank=int(row['rank']),
                corridor_type='intra_province'
            ))
        
        inter_records = []
        for _, row in result['inter_province'].iterrows():
            inter_records.append(CityCorridorRecord(
                send_city=str(row['send_city']),
                arrive_city=str(row['arrive_city']),
                flow=float(row['flow']),
                rank=int(row['rank']),
                corridor_type='inter_province'
            ))
        
        return CityCorridorResponse(
            period_type=request.period_type,
            date_mode=request.date_mode.value,
            topk_intra=request.topk_intra,
            topk_inter=request.topk_inter,
            intra_province=intra_records,
            inter_province=inter_records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

