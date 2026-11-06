cmake_minimum_required(VERSION 3.20)
project(MarketTraceEngine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler warning flags
if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/engine/include)

# Core engine library
add_library(markettrace_engine
    engine/src/envelope.cpp
    engine/src/order_book.cpp
)

# Main executable / CLI entry point
add_executable(markettrace_cli
    engine/src/main.cpp
)
target_link_libraries(markettrace_cli PRIVATE markettrace_engine)

# Tests
enable_testing()
add_executable(engine_contract_test
    engine/tests/test_contract.cpp
)
target_link_libraries(engine_contract_test PRIVATE markettrace_engine)
add_test(NAME EngineContractTest COMMAND engine_contract_test)
