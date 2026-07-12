/**
 * @file pack.h
 * @brief Portable packed struct macros (GCC + MSVC)
 */
#ifndef MILI_PACK_H
#define MILI_PACK_H

#if defined(_MSC_VER)
#define MILI_PACK_BEGIN() __pragma(pack(push, 1))
#define MILI_PACK_END()   __pragma(pack(pop))
#elif defined(__GNUC__)
#define MILI_PACK_BEGIN() _Pragma("GCC diagnostic push") _Pragma("GCC diagnostic ignored \"-Wpacked\"")
#define MILI_PACK_END()   _Pragma("GCC diagnostic pop")
#else
#define MILI_PACK_BEGIN()
#define MILI_PACK_END()
#endif

#if defined(__GNUC__)
#define MILI_PACKED __attribute__((packed))
#else
#define MILI_PACKED
#endif

#endif /* MILI_PACK_H */
