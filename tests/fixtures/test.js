// Test JavaScript file for minification
function calculateSum(numbers) {
    let total = 0;
    for (let i = 0; i < numbers.length; i++) {
        total += numbers[i];
    }
    return total;
}

const result = calculateSum([1, 2, 3, 4, 5]);
console.log('Sum:', result);

// Export for module systems
export { calculateSum };