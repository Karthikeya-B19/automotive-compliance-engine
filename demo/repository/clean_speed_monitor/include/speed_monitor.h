#ifndef SPEED_MONITOR_H
#define SPEED_MONITOR_H

#include <stdint.h>

typedef struct {
    uint16_t current_kph;
    uint16_t maximum_kph;
} SpeedMonitor;

int update_speed(SpeedMonitor *monitor, uint16_t measured_kph);

#endif
