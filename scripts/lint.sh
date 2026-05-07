#!/usr/bin/env bash
# Ruff 代码质量检查和修复脚本
# 使用方式: ./scripts/lint.sh [check|fix|format]

set -e

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

function print_header() {
    echo -e "${COLOR_BLUE}================================${COLOR_RESET}"
    echo -e "${COLOR_BLUE}$1${COLOR_RESET}"
    echo -e "${COLOR_BLUE}================================${COLOR_RESET}"
}

function print_success() {
    echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"
}

function print_error() {
    echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"
}

function print_warning() {
    echo -e "${COLOR_YELLOW}⚠️  $1${COLOR_RESET}"
}

function check_only() {
    print_header "运行 Ruff Lint 检查（仅检查，不修复）"

    if ruff check . --statistics; then
        print_success "Lint 检查通过"
    else
        print_error "Lint 检查失败"
        echo ""
        print_warning "运行 './scripts/lint.sh fix' 可自动修复部分问题"
        exit 1
    fi

    echo ""
    print_header "运行 Ruff 格式检查（仅检查，不格式化）"

    if ruff format --check .; then
        print_success "格式检查通过"
    else
        print_error "格式检查失败"
        echo ""
        print_warning "运行 './scripts/lint.sh format' 可自动格式化代码"
        exit 1
    fi
}

function fix_issues() {
    print_header "运行 Ruff Lint 并自动修复"

    if ruff check --fix .; then
        print_success "Lint 检查并修复完成"
    else
        print_warning "部分问题无法自动修复，请手动处理"
    fi
}

function format_code() {
    print_header "运行 Ruff 代码格式化"

    if ruff format .; then
        print_success "代码格式化完成"
    else
        print_error "代码格式化失败"
        exit 1
    fi
}

function full_check_and_fix() {
    print_header "完整的代码质量检查和修复"

    echo ""
    print_header "步骤 1/3: Lint 检查和修复"
    ruff check --fix . || print_warning "部分 lint 问题需要手动修复"

    echo ""
    print_header "步骤 2/3: 代码格式化"
    ruff format .

    echo ""
    print_header "步骤 3/3: 最终验证"
    if ruff check . && ruff format --check .; then
        echo ""
        print_success "🎉 所有检查通过！代码质量良好！"
    else
        echo ""
        print_warning "仍有部分问题需要手动修复"
        exit 1
    fi
}

# 主逻辑
case "${1:-check}" in
    check)
        check_only
        ;;
    fix)
        fix_issues
        ;;
    format)
        format_code
        ;;
    all)
        full_check_and_fix
        ;;
    *)
        echo "使用方式: $0 [check|fix|format|all]"
        echo ""
        echo "  check   - 仅检查，不修复（默认）"
        echo "  fix     - 检查并自动修复 lint 问题"
        echo "  format  - 自动格式化代码"
        echo "  all     - 执行完整的检查、修复和格式化"
        exit 1
        ;;
esac
