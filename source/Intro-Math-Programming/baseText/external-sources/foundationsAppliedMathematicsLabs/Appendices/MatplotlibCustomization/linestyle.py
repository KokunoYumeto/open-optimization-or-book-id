import numpy as np
from matplotlib import pyplot as plt

plt.rcParams["pdf.fonttype"] = 42

colors = np.array(["k", "g", "b", "r", "c", "m", "y", "w"])
x = np.linspace(0, 5, 10)
y = np.ones(10)
ls = np.array(["-.", ":", "o", "s", "*", "H", "x", "D"])

for i in range(len(colors)):
    plt.plot(x, i*y, colors[i] + ls[i])

plt.axis([-1, 6, -1, 8])
plt.savefig(
    "linestyle.pdf",
    format="pdf",
    metadata={"CreationDate": None, "ModDate": None},
)
plt.close()
