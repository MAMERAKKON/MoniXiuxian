"""验证配方脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[:3]}")

from xiuxian_v3.application.services.recipe_manager import RecipeManager


def main():
    """主函数"""
    print("=" * 60)
    print("炼丹配方验证工具")
    print("=" * 60)
    print()
    
    # 创建配方管理器
    manager = RecipeManager()
    
    try:
        # 加载配方
        print("正在加载配方...")
        recipes = manager.load_recipes()
        print(f"成功加载 {len(recipes)} 个配方")
        print()
        
        # 验证所有配方
        print("正在验证配方...")
        print("-" * 60)
        results = manager.validate_all_recipes()
        
        total_errors = 0
        total_warnings = 0
        
        for recipe_id, result in results.items():
            recipe = manager.get_recipe_by_id(recipe_id)
            print(f"\n配方: {recipe.name} ({recipe_id})")
            print(f"  品质: {recipe.rank}")
            print(f"  等级要求: {recipe.level_required}")
            print(f"  成功率: {recipe.success_rate}%")
            print(f"  成本: {recipe.cost}")
            print(f"  材料: {recipe.materials}")
            
            if result.errors:
                print(f"  ❌ 错误 ({len(result.errors)}):")
                for error in result.errors:
                    print(f"     - {error}")
                total_errors += len(result.errors)
            
            if result.warnings:
                print(f"  ⚠️  警告 ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"     - {warning}")
                total_warnings += len(result.warnings)
            
            if result.is_valid and not result.warnings:
                print(f"  ✅ 验证通过")
        
        print()
        print("=" * 60)
        print(f"验证完成:")
        print(f"  总配方数: {len(recipes)}")
        print(f"  总错误数: {total_errors}")
        print(f"  总警告数: {total_warnings}")
        
        if total_errors == 0:
            print("\n✅ 所有配方验证通过！")
            return 0
        else:
            print(f"\n❌ 发现 {total_errors} 个错误，请修复后重试")
            return 1
            
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
