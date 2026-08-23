import numpy as np
from matplotlib import pyplot as plt

plt.rcParams["pdf.fonttype"] = 42

colors = np.array(["k", "g", "b", "r", "c", "m", "y", "w"])
x = np.linspace(0, 5, 1000)
y = np.ones(1000)
lw = np.linspace(.5, 15, 8)

for i in range(len(colors)):
    plt.plot(x, i*y, colors[i], linewidth=lw[i])

plt.ylim([-1, 8])
plt.savefig(
    "linewidth.pdf",
    format="pdf",
    metadata={"CreationDate": None, "ModDate": None},
)
plt.close()
