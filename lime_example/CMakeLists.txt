cmake_minimum_required(VERSION 3.0)
project(lime_example)

add_custom_command(OUTPUT calc.hpp COMMAND limecc "${CMAKE_CURRENT_SOURCE_DIR}/calc.yll" DEPENDS calc.yll)

add_executable(lime_example calc.hpp main.cpp)
