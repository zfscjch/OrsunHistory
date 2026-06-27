export async function isAdmin(userId) {
    try {
        const response = await fetch("/admin/check", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({"userID": userId})
        });
        const result = await response.json();
        return result.isAdmin;
    } catch (error) {
        console.log(error);
        return undefined;
    }
}