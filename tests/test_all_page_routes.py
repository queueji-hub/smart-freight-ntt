import importlib
from Dashboard import PAGE_ROUTES, ERP_MODULES


def test_all_page_routes_exist_and_callable():
    for page_id, (module_path, fn_name) in PAGE_ROUTES.items():
        module = importlib.import_module(module_path)
        assert hasattr(module, fn_name), f"Module {module_path} is missing {fn_name} for page {page_id}"
        fn = getattr(module, fn_name)
        assert callable(fn), f"{module_path}.{fn_name} is not callable"


def test_all_erp_modules_covered():
    for group, modules in ERP_MODULES.items():
        for page_id, label, module_name in modules:
            assert page_id in PAGE_ROUTES, f"Page {page_id} in group {group} is not mapped in PAGE_ROUTES"
