#include "../include/speed_monitor.h"

int update_speed(SpeedMonitor *monitor, uint16_t measured_kph)
{
    if (monitor == 0) {
        return -1;
    }

    if (measured_kph > monitor->maximum_kph) {
        monitor->current_kph = monitor->maximum_kph;
        return 1;
    }

    monitor->current_kph = measured_kph;
    return 0;
}
