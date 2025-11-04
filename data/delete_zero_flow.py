#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除 geo_points.db 数据库中所有零流量数据的脚本
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime


def backup_database(db_path):
    """备份数据库文件"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📦 正在备份数据库到: {backup_path}")

    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库备份完成: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        return None


def analyze_zero_flow_data(db_path):
    """分析零流量数据"""
    print("🔍 分析零流量数据...")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # 统计零流量数据
        result = conn.execute(
            """
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN flow = 0 THEN 1 END) as zero_flow_records,
                COUNT(CASE WHEN flow > 0 THEN 1 END) as non_zero_flow_records,
                ROUND(COUNT(CASE WHEN flow = 0 THEN 1 END) * 100.0 / COUNT(*), 2) as zero_percentage
            FROM dyna
        """
        ).fetchone()

        total = result["total_records"]
        zero_count = result["zero_flow_records"]
        non_zero_count = result["non_zero_flow_records"]
        zero_percentage = result["zero_percentage"]

        print(f"📊 当前数据统计:")
        print(f"  总记录数: {total:,}")
        print(f"  零流量记录: {zero_count:,} ({zero_percentage}%)")
        print(f"  非零流量记录: {non_zero_count:,} ({100-zero_percentage}%)")

        # 估算删除后的效果
        estimated_size = (non_zero_count / total) * os.path.getsize(db_path)
        current_size = os.path.getsize(db_path)
        size_reduction = current_size - estimated_size

        print(f"\n📈 预估删除效果:")
        print(f"  当前文件大小: {current_size / (1024**3):.2f} GB")
        print(f"  预估删除后大小: {estimated_size / (1024**3):.2f} GB")
        print(
            f"  预估节省空间: {size_reduction / (1024**3):.2f} GB ({size_reduction/current_size*100:.1f}%)"
        )

        return {
            "total": total,
            "zero_count": zero_count,
            "non_zero_count": non_zero_count,
            "zero_percentage": zero_percentage,
        }


def delete_zero_flow_data(db_path, dry_run=False):
    """删除零流量数据"""
    print(f"\n{'🔍 模拟删除' if dry_run else '🗑️ 开始删除'}零流量数据...")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # 开始事务
        conn.execute("BEGIN TRANSACTION")

        try:
            if dry_run:
                # 模拟模式：只统计要删除的记录
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM dyna WHERE flow = 0"
                ).fetchone()
                print(f"  将删除 {result['count']:,} 条零流量记录")
            else:
                # 实际删除
                print("  正在删除零流量记录...")
                cursor = conn.execute("DELETE FROM dyna WHERE flow = 0")
                deleted_count = cursor.rowcount
                print(f"  ✅ 已删除 {deleted_count:,} 条零流量记录")

                # 提交事务
                conn.commit()
                print("  ✅ 事务已提交")

                # 检查磁盘空间，如果空间不足则跳过VACUUM
                import shutil

                free_space = shutil.disk_usage("/").free
                current_size = os.path.getsize(db_path)

                if free_space > current_size * 2:  # 需要至少2倍当前文件大小的空间
                    print("  🔧 正在执行VACUUM以回收空间...")
                    conn.execute("VACUUM")
                    print("  ✅ VACUUM完成")
                else:
                    print("  ⚠️ 磁盘空间不足，跳过VACUUM操作")
                    print(f"    可用空间: {free_space / (1024**3):.2f} GB")
                    print(f"    需要空间: {current_size * 2 / (1024**3):.2f} GB")
                    print("    建议稍后在空间充足时手动执行VACUUM")

                return deleted_count

        except Exception as e:
            print(f"  ❌ 操作失败: {e}")
            conn.rollback()
            print("  🔄 事务已回滚")
            raise


def verify_deletion(db_path):
    """验证删除结果"""
    print("\n🔍 验证删除结果...")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # 检查是否还有零流量记录
        zero_count = conn.execute(
            "SELECT COUNT(*) as count FROM dyna WHERE flow = 0"
        ).fetchone()["count"]
        total_count = conn.execute("SELECT COUNT(*) as count FROM dyna").fetchone()[
            "count"
        ]

        print(f"📊 删除后统计:")
        print(f"  总记录数: {total_count:,}")
        print(f"  零流量记录: {zero_count:,}")

        if zero_count == 0:
            print("  ✅ 所有零流量数据已成功删除")
        else:
            print(f"  ⚠️ 仍有 {zero_count} 条零流量记录")

        # 检查文件大小
        file_size = os.path.getsize(db_path)
        print(f"  当前文件大小: {file_size / (1024**3):.2f} GB")


def main():
    """主函数"""
    print("🚀 零流量数据删除脚本")
    print("=" * 60)

    db_path = "geo_points.db"

    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return 1

    # 1. 分析零流量数据
    stats = analyze_zero_flow_data(db_path)

    if stats["zero_count"] == 0:
        print("✅ 数据库中没有零流量数据，无需删除")
        return 0

    # 2. 询问用户确认
    print(f"\n⚠️ 确认删除 {stats['zero_count']:,} 条零流量记录吗？")
    print("这将:")
    print(f"  - 删除 {stats['zero_percentage']}% 的数据")
    print(f"  - 显著减小数据库文件大小")
    print(f"  - 提高查询性能")
    print(f"  - 不会影响分析结果的正确性")

    # 3. 先进行模拟删除
    print(f"\n🔍 先进行模拟删除...")
    delete_zero_flow_data(db_path, dry_run=True)

    # 4. 询问是否继续
    response = input(f"\n是否继续执行实际删除？(y/N): ").strip().lower()
    if response not in ["y", "yes"]:
        print("❌ 操作已取消")
        return 0

    # 5. 备份数据库
    backup_path = backup_database(db_path)
    if not backup_path:
        print("❌ 备份失败，取消删除操作")
        return 1

    try:
        # 6. 执行删除
        deleted_count = delete_zero_flow_data(db_path, dry_run=False)

        # 7. 验证结果
        verify_deletion(db_path)

        print(f"\n✅ 零流量数据删除完成！")
        print(f"  删除了 {deleted_count:,} 条记录")
        print(f"  备份文件: {backup_path}")

        return 0

    except Exception as e:
        print(f"\n❌ 删除过程中发生错误: {e}")
        print(f"💡 可以从备份文件恢复: {backup_path}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
