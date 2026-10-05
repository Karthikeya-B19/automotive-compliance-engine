#include "../include/sensor.h"

int read_sensor_value(const int *samples, size_t sample_count)
{
    if (sample_count == 0U) {
        return -1;
    }

    return samples[0];
}
