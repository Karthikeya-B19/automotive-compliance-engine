#ifndef SENSOR_H
#define SENSOR_H

#include <stddef.h>

int copy_sensor_name(char *destination, const char *source);
int read_sensor_value(const int *samples, size_t sample_count);

#endif
