#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions
"""

from datetime import datetime, timezone


def iso_to_epoch(s: str) -> int:
    """
    Convert ISO8601 timestamp to Unix epoch
    Supports trailing 'Z' and handles timezone
    """
    if s.endswith("Z"):
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def extract_province(city_name: str) -> str:
    """
    Extract province from city name (simplified version)
    In production, use a proper province mapping table
    """
    provinces = [
        '北京', '天津', '上海', '重庆',
        '河北', '山西', '辽宁', '吉林', '黑龙江',
        '江苏', '浙江', '安徽', '福建', '江西', '山东',
        '河南', '湖北', '湖南', '广东', '海南',
        '四川', '贵州', '云南', '陕西', '甘肃', '青海',
        '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'
    ]
    
    for province in provinces:
        if city_name.startswith(province):
            return province
    
    # If no match, return first 2 characters as identifier
    return city_name[:2] if len(city_name) >= 2 else city_name

