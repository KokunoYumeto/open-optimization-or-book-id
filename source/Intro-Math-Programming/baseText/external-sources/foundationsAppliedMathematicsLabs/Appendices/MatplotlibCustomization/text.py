import numpy as np
from matplotlib import pyplot as plt

plt.rcParams["pdf.fonttype"] = 42

colors = np.array(["k", "g", "b", "r", "c", "m", "y", "w"])
x = np.linspace(0, 5, 10)
y = np.ones(10)
ls = np.array(["-.", ":", "o", "s", "*", "H", "x", "D"])

for i in range(len(colors)):
    plt.plot(x, i*y, colors[i] + ls[i])

plt.title("Plot Berbagai Gaya Garis", fontsize=20, color="gold")
plt.xlabel("sumbu x", fontsize=10, color="darkcyan")
plt.ylabel("sumbu y", fontsize=10, color="darkcyan")

plt.axis([-1, 6, -1, 8])
plt.savefig(
    "text.pdf",
    format="pdf",
    metadata={"CreationDate": None, "ModDate": None},
)
plt.close()
