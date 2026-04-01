import { AIModel, DEFAULT_MODELS } from './models'
import { devLog } from './devLog'

class ModelService {
  private models: AIModel[] = [...DEFAULT_MODELS]
  private availableModels: AIModel[] = []

  async getAllModels(): Promise<AIModel[]> {
    // In a real implementation, this would fetch from the backend
    // For now, return the default models
    return this.models
  }

  async getAvailableModels(): Promise<AIModel[]> {
    // Since Ollama is not available, focus on cloud models
    const available: AIModel[] = []
    
    for (const model of this.models) {
      if (model.type === 'local') {
        // Allow backend-default model specifically
        if (model.id === 'backend-default') {
          available.push({ ...model, isAvailable: true })
          continue
        }
        // Skip other local models since Ollama is not available
        devLog(`Skipping local model ${model.id} - Ollama not available`)
        continue
      } else {
        // For cloud models, check if API keys are configured
        const hasApiKey = this.checkApiKey(model.provider)
        if (hasApiKey) {
          available.push({ ...model, isAvailable: true })
        } else {
          available.push({ ...model, isAvailable: false })
        }
      }
    }
    
    this.availableModels = available
    return available
  }

  async getModelById(id: string): Promise<AIModel | null> {
    const models = await this.getAllModels()
    return models.find(model => model.id === id) || null
  }

  async addModel(model: AIModel): Promise<void> {
    this.models.push(model)
  }

  async removeModel(id: string): Promise<void> {
    this.models = this.models.filter(model => model.id !== id)
  }

  private checkApiKey(provider: string): boolean {
    // Check if API keys are configured in environment
    switch (provider) {
      case 'openai':
        return !!process.env.NEXT_PUBLIC_OPENAI_API_KEY
      case 'anthropic':
        return !!process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY
      case 'gemini':
        return !!process.env.NEXT_PUBLIC_GEMINI_API_KEY
      default:
        return false
    }
  }

  async checkModelHealth(modelId: string): Promise<boolean> {
    const model = await this.getModelById(modelId)
    if (!model) return false

    if (model.type === 'local') {
      // Ollama is not available, so local models are not healthy
      devLog(`Local model ${modelId} is not available - Ollama not installed`)
      return false
    } else {
      // For cloud models, check if API keys are configured
      return this.checkApiKey(model.provider)
    }
  }

  async checkOllamaConnection(): Promise<boolean> {
    // Ollama is not available on this system
    devLog('Ollama is not installed on this system')
    return false
  }

  async refreshModels(): Promise<AIModel[]> {
    // Refresh available models and return them
    return await this.getAvailableModels()
  }

  async getCloudModels(): Promise<AIModel[]> {
    const allModels = await this.getAllModels()
    return allModels.filter(model => model.category === 'cloud')
  }

  async getLocalModels(): Promise<AIModel[]> {
    const allModels = await this.getAllModels()
    return allModels.filter(model => model.category === 'ollama')
  }
}

export const modelService = new ModelService()
