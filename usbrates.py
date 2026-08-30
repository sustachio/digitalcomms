import numpy as np
import adi
import matplotlib.pyplot as plt
import time

sample_rate = 5e6 # Hz
center_freq = 900e6 # Hz

sdr = adi.Pluto("ip:192.168.2.1")

count = 50

#for buffer_size in [256, 512, 1024, 1024*2, 1024*4, 1024*8, 1024*16, 1024*32, 1024*64, 1024*128]:
#for buffer_size in [1024*32, 1024*64]:
#for buffer_size in [1024, 1024*4]:
#for buffer_size in [1024*32, 1024*64, 1024*128, 1024*256, 1024*512, 1024*1024]:
for buffer_size in [256, 1024*2, 1024*16, 1024*32, 1024*64, 1024*128]:
  freqs = list(range(int(3e6),int(8e6),int(200e3)))
  percents = []
  for rate in freqs:
    sdr.sample_rate = int(rate)
    sdr.rx_rf_bandwidth = int(rate) # filter cutoff, just set it to the same as sample rate
    sdr.rx_lo = int(center_freq)
    sdr.rx_buffer_size = buffer_size # this is the buffer the Pluto uses to buffer samples

    time.sleep(0.05)

    for _ in range(3):
      sdr.rx()
    
    l=0
    s = time.perf_counter()
    for _ in range(count):
      l+=len(sdr.rx())
    e = time.perf_counter()
    t = e-s

    real_rate = l / t;
    
    percents.append(100 * real_rate / rate)
    #percents.append(real_rate)

    print(f"buffer: {buffer_size}, rate: {rate}: {real_rate:.4f}S/s  {100 * real_rate/rate:.4f}%")

    sdr.rx_destroy_buffer()

  #plt.plot(freqs, percents, label=str(buffer_size), marker="o")
  plt.plot(freqs, percents, label=str(buffer_size))
  
plt.title("Can USB Keep Up? (no extra computation)")
  
plt.xlabel("Requested sample rate (Hz)")
#plt.ylabel("Real sample rate (Hz)")
plt.ylabel("% of requested sample rate")
  
plt.legend(title="Buffer Size")
plt.show()