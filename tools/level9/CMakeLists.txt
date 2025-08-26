set(SOURCES
    bitmap.c
    level9.c
    talkie.c
)

add_executable(level9 ${SOURCES})
target_link_libraries(level9 PRIVATE m)
